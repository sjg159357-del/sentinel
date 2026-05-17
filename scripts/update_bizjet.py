#!/usr/bin/env python3
"""
SENTINEL 비즈니스 제트 활동 지수 자동 업데이트
주 1회 실행 (GitHub Actions)

데이터 소스:
  - OpenSky Network API (무료, CORS 지원): 현재 비행 중인 항공기 목록
  - adsbdb.com API (무료): ICAO24 코드 → 항공기 타입 조회
  - 캐시 파일 (sentinel-data.json 내 bizjet_cache): 반복 조회 방지

지수 계산:
  - 각 국가 등록 비즈니스 제트 중 현재 비행 중인 비율
  - 절대 수치보다 상대적 활동성 변화가 중요
  - 0-100 점수로 정규화 (높을수록 엘리트 이탈 활발)

한계:
  - adsbdb.com은 모든 ICAO24 코드를 커버하지 않음 (약 70-80%)
  - 러시아(RF-), 이란(EP-) 등 일부 국가는 ADS-B 수신 제한
  - 결과는 추세 지표로만 활용 (절대값 신뢰 불가)
"""

import json
import requests
import time
from datetime import date, datetime
from collections import Counter, defaultdict

TODAY = str(date.today())
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SentinelBot/1.0)"}

# ── 비즈니스 제트 ICAO 타입코드 목록 ────────────────────────────────────────
# 출처: ICAO Doc 8643 + 업계 분류 기준
BIZ_JET_TYPES = {
    # Gulfstream (대형 비즈니스 제트)
    "GL5T", "GL7T", "GL9T", "GLEX", "G150", "G200", "G280",
    "G350", "G400", "G450", "G500", "G550", "G600", "G650",
    # Bombardier Challenger / Global
    "CL30", "CL35", "CL60",
    # Dassault Falcon
    "F2TH", "F7X", "F8X", "F900", "FA50", "FA7X", "FA8X",
    # Cessna Citation
    "C25A", "C25B", "C25C", "C25M", "C510", "C525", "C526",
    "C55B", "C560", "C56X", "C680", "C68A", "C700", "C750",
    # Learjet
    "LJ23", "LJ24", "LJ25", "LJ28", "LJ31", "LJ35", "LJ36",
    "LJ40", "LJ45", "LJ55", "LJ60", "LJ70", "LJ75", "LJ85",
    # Embraer Legacy / Phenom / Praetor
    "E135", "E145", "E50P", "E545", "E550", "E55P", "E75L", "E75S",
    # Pilatus
    "PC12", "PC24",
    # HondaJet
    "HDJT",
    # Beechcraft / Hawker
    "BE40", "BE45", "H25A", "H25B", "H25C", "HS25",
    # IAI Astra / Galaxy
    "ASTR", "G100",
    # Daher TBM (터보프롭이지만 비즈니스 항공 포함)
    "TBM7", "TBM8", "TBM9",
}

# ── 국가명 → ISO2 매핑 (OpenSky origin_country 기준) ────────────────────────
COUNTRY_NAME_TO_ISO2 = {
    "United States": "US", "Russia": "RU", "China": "CN", "Germany": "DE",
    "United Kingdom": "GB", "France": "FR", "Turkey": "TR", "India": "IN",
    "Brazil": "BR", "Canada": "CA", "Australia": "AU", "Japan": "JP",
    "South Korea": "KR", "Republic of Korea": "KR", "Mexico": "MX",
    "Argentina": "AR", "Saudi Arabia": "SA", "United Arab Emirates": "AE",
    "Switzerland": "CH", "Sweden": "SE", "Netherlands": "NL", "Poland": "PL",
    "Austria": "AT", "Belgium": "BE", "Spain": "ES", "Italy": "IT",
    "Portugal": "PT", "Greece": "GR", "Hungary": "HU", "Romania": "RO",
    "Ukraine": "UA", "Belarus": "BY", "Kazakhstan": "KZ", "Uzbekistan": "UZ",
    "Iran": "IR", "Iraq": "IQ", "Egypt": "EG", "Nigeria": "NG",
    "South Africa": "ZA", "Kenya": "KE", "Ethiopia": "ET",
    "Venezuela": "VE", "Colombia": "CO", "Peru": "PE", "Chile": "CL",
    "Indonesia": "ID", "Malaysia": "MY", "Thailand": "TH", "Vietnam": "VN",
    "Pakistan": "PK", "Bangladesh": "BD", "Singapore": "SG",
    "New Zealand": "NZ", "Ireland": "IE", "Malta": "MT",
    "Luxembourg": "LU", "Cyprus": "CY", "Iceland": "IS",
    "Georgia": "GE", "Armenia": "AM", "Azerbaijan": "AZ",
    "Lebanon": "LB", "Syria": "SY", "Libya": "LY", "Sudan": "SD",
    "Zimbabwe": "ZW", "Myanmar": "MM", "Cuba": "CU", "Bolivia": "BO",
    "Laos": "LA", "Tajikistan": "TJ", "Afghanistan": "AF",
    "Sri Lanka": "LK", "Tunisia": "TN", "Algeria": "DZ",
    "Morocco": "MA", "Angola": "AO", "Mozambique": "MZ",
    "Zambia": "ZM", "Uganda": "UG", "Tanzania": "TZ",
    "Taiwan": "TW", "Hong Kong": "HK",
}

print(f"✈️  비즈니스 제트 활동 지수 업데이트 시작: {TODAY}")
print("=" * 60)

# ── 기존 데이터 로드 ────────────────────────────────────────────────────────
with open("sentinel-data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 캐시: ICAO24 → 타입코드 (이미 조회한 항공기는 재조회 불필요)
bizjet_cache = data.get("bizjet_cache", {})
print(f"  기존 캐시: {len(bizjet_cache)}개 항공기")


# ── 1단계: OpenSky states/all 조회 ──────────────────────────────────────────
print("\n📡 OpenSky 현재 비행 중인 항공기 조회...")
try:
    r = requests.get(
        "https://opensky-network.org/api/states/all",
        headers=HEADERS, timeout=30
    )
    r.raise_for_status()
    opensky_data = r.json()
    states = opensky_data.get("states", [])
    print(f"  현재 비행 중: {len(states)}대")
except Exception as e:
    print(f"  ❌ OpenSky 조회 실패: {e}")
    states = []

# 비행 중인 항공기만 필터링 (on_ground=False)
flying = [s for s in states if not s[8]]
print(f"  실제 비행 중: {len(flying)}대")

# ICAO24 → origin_country 매핑
icao24_to_country = {s[0]: s[2] for s in flying if s[0] and s[2]}


# ── 2단계: 새 ICAO24 코드의 타입 조회 (adsbdb.com) ──────────────────────────
print("\n🔍 신규 항공기 타입 조회 (adsbdb.com)...")

new_icao24 = [
    icao24 for icao24 in icao24_to_country.keys()
    if icao24 not in bizjet_cache
]
print(f"  캐시 미등록 항공기: {len(new_icao24)}대")

# 최대 500개만 조회 (API 부하 방지)
MAX_LOOKUP = 500
lookup_targets = new_icao24[:MAX_LOOKUP]
print(f"  이번 회차 조회: {len(lookup_targets)}대")

lookup_count = 0
error_count = 0

for icao24 in lookup_targets:
    try:
        r = requests.get(
            f"https://api.adsbdb.com/v0/aircraft/{icao24}",
            headers=HEADERS, timeout=8
        )
        if r.status_code == 200:
            d = r.json()
            aircraft = d.get("response", {}).get("aircraft", {})
            icao_type = aircraft.get("icao_type", "")
            bizjet_cache[icao24] = icao_type if icao_type else "UNKNOWN"
            lookup_count += 1
        elif r.status_code == 404:
            bizjet_cache[icao24] = "UNKNOWN"
        else:
            error_count += 1
    except Exception:
        error_count += 1
    
    time.sleep(0.15)  # 초당 약 6.7 요청

print(f"  조회 완료: {lookup_count}대, 오류: {error_count}대")


# ── 3단계: 비즈니스 제트 국가별 집계 ────────────────────────────────────────
print("\n📊 국가별 비즈니스 제트 집계...")

# 현재 비행 중인 비즈니스 제트 집계
biz_by_country = Counter()
total_biz = 0

for icao24, country in icao24_to_country.items():
    icao_type = bizjet_cache.get(icao24, "")
    if icao_type in BIZ_JET_TYPES:
        iso2 = COUNTRY_NAME_TO_ISO2.get(country)
        if iso2:
            biz_by_country[iso2] += 1
            total_biz += 1

print(f"  현재 비행 중인 비즈니스 제트: {total_biz}대")
print(f"  집계된 국가: {len(biz_by_country)}개국")

# 상위 15개국 출력
print("\n  상위 15개국:")
for iso2, cnt in biz_by_country.most_common(15):
    print(f"    {iso2}: {cnt}대")


# ── 4단계: 0-100 지수 계산 ──────────────────────────────────────────────────
# 미국이 압도적으로 많으므로 인구 보정 또는 상대적 순위로 정규화
# 방법: 상위 국가 대비 비율 × 100 (미국=100 기준)

us_count = biz_by_country.get("US", 1)
bizjet_index = {}

for iso2, cnt in biz_by_country.items():
    # 미국 대비 비율 (0-100)
    # 단, 미국은 세계 최대 비즈니스 항공 시장이므로 기준점으로 사용
    idx = min(100, round(cnt / us_count * 100))
    bizjet_index[iso2] = {
        "count": cnt,
        "index": idx,
        "updated": TODAY
    }


# ── 5단계: sentinel-data.json 저장 ──────────────────────────────────────────
data["bizjet_cache"] = bizjet_cache
data["bizjet"] = bizjet_index
data["_meta"]["last_bizjet_update"] = TODAY
data["_meta"]["bizjet_total_flying"] = total_biz
data["_meta"]["bizjet_cache_size"] = len(bizjet_cache)

with open("sentinel-data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 비즈니스 제트 지수 업데이트 완료")
print(f"   비행 중 비즈니스 제트: {total_biz}대")
print(f"   집계 국가: {len(bizjet_index)}개국")
print(f"   캐시 크기: {len(bizjet_cache)}개 항공기")
print(f"   sentinel-data.json 저장됨")
