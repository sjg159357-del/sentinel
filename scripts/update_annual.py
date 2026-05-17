#!/usr/bin/env python3
"""
SENTINEL 연간 지표 자동 업데이트 스크립트
주 1회 실행 (기존 수동 🔴 항목 자동화):

  ✅ 법치지수 (law)       ← World Bank WGI: GOV_WGI_RL.SC
  ✅ 민주주의지수 (demo)  ← World Bank WGI: GOV_WGI_VA.SC (Voice & Accountability)
  ✅ 가계부채 (hd)        ← BIS SDMX API: WS_TC 가계 신용/GDP
  ✅ 기업부채 (cd)        ← BIS SDMX API: WS_TC 비금융기업 신용/GDP
  ✅ 3년 절하율 (dep3y)   ← World Bank PA.NUS.FCRF 연간 환율로 계산
  ✅ 시민 탈출 (citizen)  ← World Bank SM.POP.NETM 순이민 데이터 → 0-100 지수화
"""

import json
import requests
import time
from datetime import date
from xml.etree import ElementTree as ET

TODAY = str(date.today())
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SentinelBot/1.0)"}

# ── 기존 데이터 로드 ────────────────────────────────────────────────────────
with open("sentinel-data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# annual 섹션이 없으면 초기화
if "annual" not in data:
    data["annual"] = {}

annual = data["annual"]

print(f"📅 연간 지표 업데이트 시작: {TODAY}")
print("=" * 60)

# ── 대상 국가 목록 ──────────────────────────────────────────────────────────
# ISO2 → ISO3 매핑 (World Bank는 ISO3 사용)
ISO2_TO_ISO3 = {
    "AF":"AFG","AR":"ARG","AU":"AUS","BD":"BGD","BE":"BEL","BO":"BOL",
    "BR":"BRA","BY":"BLR","CA":"CAN","CH":"CHE","CN":"CHN","CO":"COL",
    "CU":"CUB","DE":"DEU","EG":"EGY","ET":"ETH","GE":"GEO","GH":"GHA",
    "HU":"HUN","ID":"IDN","IN":"IND","IR":"IRN","JP":"JPN","KE":"KEN",
    "KH":"KHM","KR":"KOR","KZ":"KAZ","LA":"LAO","LB":"LBN","LK":"LKA",
    "MA":"MAR","MM":"MMR","MX":"MEX","MY":"MYS","NG":"NGA","NP":"NPL",
    "NZ":"NZL","PE":"PER","PK":"PAK","PL":"POL","RO":"ROU","RU":"RUS",
    "SA":"SAU","SD":"SDN","SE":"SWE","SG":"SGP","SY":"SYR","TH":"THA",
    "TJ":"TJK","TN":"TUN","TR":"TUR","TW":"TWN","UA":"UKR","US":"USA",
    "UZ":"UZB","VE":"VEN","VN":"VNM","ZA":"ZAF","ZM":"ZMB","ZW":"ZWE",
    "GB":"GBR","FR":"FRA","IT":"ITA","ES":"ESP","NL":"NLD","PT":"PRT",
    "GR":"GRC",
}

# BIS는 ISO2 사용
BIS_COUNTRIES = [
    "AR","AU","BR","CA","CN","CO","DE","FR","GB","HU","ID","IN",
    "JP","KR","MX","MY","NZ","PL","RO","RU","SA","SE","SG","TH",
    "TR","UA","US","ZA","IT","ES","NL","PT","GR","CH","BE",
    # 이머징 추가
    "EG","NG","PK","BD","LK","KZ","VN","BY","HU","RO",
]

ALL_COUNTRIES_ISO2 = list(ISO2_TO_ISO3.keys())


# ══════════════════════════════════════════════════════
# 1. World Bank WGI — 법치지수 (law) + 민주주의지수 (demo)
# ══════════════════════════════════════════════════════
print("\n⚖️  World Bank WGI 법치·민주주의 지수 업데이트:")

def get_wgi_batch(indicator, countries_iso3, label):
    """World Bank WGI 지표를 여러 국가 동시 조회"""
    # 최대 60개씩 나눠서 요청
    results = {}
    batch_size = 60
    country_list = list(countries_iso3)
    
    for i in range(0, len(country_list), batch_size):
        batch = country_list[i:i+batch_size]
        iso3_str = ";".join(batch)
        url = (f"https://api.worldbank.org/v2/country/{iso3_str}"
               f"/indicator/{indicator}?format=json&mrv=3&per_page=200")
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            d = r.json()
            if isinstance(d, list) and len(d) > 1 and d[1]:
                for item in d[1]:
                    iso3 = item.get("countryiso3code")
                    val = item.get("value")
                    if iso3 and val is not None and iso3 not in results:
                        results[iso3] = round(float(val), 1)
        except Exception as e:
            print(f"  ⚠️  WGI {label} 배치 실패: {e}")
        time.sleep(0.5)
    
    return results

# ISO3 목록 준비
all_iso3 = list(ISO2_TO_ISO3.values())

# 법치지수 (0-100 점수)
law_scores = get_wgi_batch("GOV_WGI_RL.SC", all_iso3, "법치")
print(f"  ✅ 법치지수: {len(law_scores)}개국 수집")

# 민주주의지수 (Voice & Accountability, 0-100 점수)
demo_scores = get_wgi_batch("GOV_WGI_VA.SC", all_iso3, "민주주의")
print(f"  ✅ 민주주의지수: {len(demo_scores)}개국 수집")

# ISO3 → ISO2 역매핑
ISO3_TO_ISO2 = {v: k for k, v in ISO2_TO_ISO3.items()}

# annual 데이터에 저장
for iso3, val in law_scores.items():
    iso2 = ISO3_TO_ISO2.get(iso3)
    if iso2:
        if iso2 not in annual:
            annual[iso2] = {}
        annual[iso2]["law"] = val
        annual[iso2]["law_src"] = "WB_WGI"

for iso3, val in demo_scores.items():
    iso2 = ISO3_TO_ISO2.get(iso3)
    if iso2:
        if iso2 not in annual:
            annual[iso2] = {}
        annual[iso2]["demo"] = val
        annual[iso2]["demo_src"] = "WB_WGI_VA"

# 샘플 출력
for iso2 in ["KR", "RU", "TR", "AR", "IR"]:
    if iso2 in annual:
        print(f"  {iso2}: law={annual[iso2].get('law','?')} demo={annual[iso2].get('demo','?')}")


# ══════════════════════════════════════════════════════
# 2. BIS SDMX API — 가계부채 (hd) + 기업부채 (cd)
# ══════════════════════════════════════════════════════
print("\n🏦 BIS 가계부채·기업부채 업데이트:")

def get_bis_credit(country_iso2, sector):
    """
    BIS WS_TC 데이터셋에서 신용/GDP 비율 가져오기
    sector: 'H'=가계, 'N'=비금융기업
    시리즈 키: Q.{국가}.{sector}.A.M.770.A
    """
    url = f"https://stats.bis.org/api/v1/data/WS_TC/Q.{country_iso2}.{sector}.A.M.770.A"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.content)
        obs_list = []
        for obs in root.iter():
            if obs.tag.endswith("Obs"):
                tp = obs.get("TIME_PERIOD")
                val = obs.get("OBS_VALUE")
                if tp and val:
                    obs_list.append((tp, float(val)))
        if not obs_list:
            return None
        obs_list.sort(key=lambda x: x[0], reverse=True)
        return round(obs_list[0][1], 1)
    except Exception as e:
        return None

hd_count = 0
cd_count = 0

for iso2 in BIS_COUNTRIES:
    # 가계부채
    hd = get_bis_credit(iso2, "H")
    if hd is not None:
        if iso2 not in annual:
            annual[iso2] = {}
        annual[iso2]["hd"] = hd
        annual[iso2]["hd_src"] = "BIS_WS_TC"
        hd_count += 1
    
    # 기업부채
    cd = get_bis_credit(iso2, "N")
    if cd is not None:
        if iso2 not in annual:
            annual[iso2] = {}
        annual[iso2]["cd"] = cd
        annual[iso2]["cd_src"] = "BIS_WS_TC"
        cd_count += 1
    
    time.sleep(0.3)  # API 부하 방지

print(f"  ✅ 가계부채: {hd_count}개국 수집")
print(f"  ✅ 기업부채: {cd_count}개국 수집")

# 샘플 출력
for iso2 in ["KR", "US", "CN", "TR", "JP"]:
    if iso2 in annual:
        print(f"  {iso2}: hd={annual[iso2].get('hd','?')} cd={annual[iso2].get('cd','?')}")


# ══════════════════════════════════════════════════════
# 3. World Bank PA.NUS.FCRF — 3년 절하율 (dep3y)
# ══════════════════════════════════════════════════════
print("\n💱 3년 절하율 (dep3y) 업데이트:")

def get_dep3y_batch(countries_iso3):
    """World Bank 연간 환율 데이터로 3년 절하율 계산"""
    results = {}
    batch_size = 60
    country_list = list(countries_iso3)
    
    for i in range(0, len(country_list), batch_size):
        batch = country_list[i:i+batch_size]
        iso3_str = ";".join(batch)
        url = (f"https://api.worldbank.org/v2/country/{iso3_str}"
               f"/indicator/PA.NUS.FCRF?format=json&mrv=5&per_page=400")
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            d = r.json()
            if not (isinstance(d, list) and len(d) > 1 and d[1]):
                continue
            
            # 국가별 연도별 환율 수집
            country_rates = {}
            for item in d[1]:
                iso3 = item.get("countryiso3code")
                yr = item.get("date")
                val = item.get("value")
                if iso3 and yr and val is not None:
                    if iso3 not in country_rates:
                        country_rates[iso3] = {}
                    country_rates[iso3][int(yr)] = float(val)
            
            # 3년 절하율 계산
            current_year = date.today().year
            for iso3, rates in country_rates.items():
                # 최신 연도와 3년 전 연도 비교
                years_available = sorted(rates.keys(), reverse=True)
                if len(years_available) >= 2:
                    latest_yr = years_available[0]
                    # 3년 전 데이터 찾기 (없으면 가장 오래된 것 사용)
                    target_yr = latest_yr - 3
                    if target_yr in rates:
                        old_rate = rates[target_yr]
                        new_rate = rates[latest_yr]
                        if old_rate > 0:
                            dep3y = round((new_rate - old_rate) / old_rate * 100, 1)
                            results[iso3] = dep3y
        except Exception as e:
            print(f"  ⚠️  dep3y 배치 실패: {e}")
        time.sleep(0.5)
    
    return results

dep3y_results = get_dep3y_batch(all_iso3)
print(f"  ✅ 3년 절하율: {len(dep3y_results)}개국 계산")

for iso3, val in dep3y_results.items():
    iso2 = ISO3_TO_ISO2.get(iso3)
    if iso2:
        if iso2 not in annual:
            annual[iso2] = {}
        annual[iso2]["dep3y"] = val
        annual[iso2]["dep3y_src"] = "WB_FCRF"

# 샘플 출력
for iso2 in ["TR", "AR", "RU", "EG", "KR"]:
    if iso2 in annual:
        print(f"  {iso2}: dep3y={annual[iso2].get('dep3y','?')}%")


# ══════════════════════════════════════════════════════
# 4. World Bank SM.POP.NETM — 시민 탈출 지수 (citizen)
# ══════════════════════════════════════════════════════
print("\n✈️  시민 탈출 지수 (citizen) 업데이트:")

def get_citizen_flight_batch(countries_iso3):
    """
    World Bank 순이민 데이터(SM.POP.NETM)를 0-100 지수로 변환
    순이민이 음수(인구 유출)일수록 높은 점수
    """
    results = {}
    batch_size = 60
    country_list = list(countries_iso3)
    
    for i in range(0, len(country_list), batch_size):
        batch = country_list[i:i+batch_size]
        iso3_str = ";".join(batch)
        
        # 순이민 데이터
        url_mig = (f"https://api.worldbank.org/v2/country/{iso3_str}"
                   f"/indicator/SM.POP.NETM?format=json&mrv=1&per_page=200")
        # 총인구 데이터 (비율 계산용)
        url_pop = (f"https://api.worldbank.org/v2/country/{iso3_str}"
                   f"/indicator/SP.POP.TOTL?format=json&mrv=1&per_page=200")
        
        try:
            r_mig = requests.get(url_mig, headers=HEADERS, timeout=20)
            r_pop = requests.get(url_pop, headers=HEADERS, timeout=20)
            
            d_mig = r_mig.json()
            d_pop = r_pop.json()
            
            mig_data = {}
            pop_data = {}
            
            if isinstance(d_mig, list) and len(d_mig) > 1 and d_mig[1]:
                for item in d_mig[1]:
                    iso3 = item.get("countryiso3code")
                    val = item.get("value")
                    if iso3 and val is not None:
                        mig_data[iso3] = float(val)
            
            if isinstance(d_pop, list) and len(d_pop) > 1 and d_pop[1]:
                for item in d_pop[1]:
                    iso3 = item.get("countryiso3code")
                    val = item.get("value")
                    if iso3 and val is not None:
                        pop_data[iso3] = float(val)
            
            for iso3, mig in mig_data.items():
                pop = pop_data.get(iso3, 10_000_000)
                if pop > 0:
                    # 순이민율 (per 1000명)
                    mig_rate = (mig / pop) * 1000
                    # 음수(유출)를 0-100 점수로 변환
                    # -10 이하 → 100점, -5 → 75점, 0 → 50점, +5 → 25점, +10 이상 → 0점
                    # 공식: score = max(0, min(100, 50 - mig_rate * 5))
                    score = max(0, min(100, round(50 - mig_rate * 5)))
                    results[iso3] = score
        
        except Exception as e:
            print(f"  ⚠️  citizen 배치 실패: {e}")
        time.sleep(0.5)
    
    return results

citizen_results = get_citizen_flight_batch(all_iso3)
print(f"  ✅ 시민 탈출 지수: {len(citizen_results)}개국 계산")

for iso3, val in citizen_results.items():
    iso2 = ISO3_TO_ISO2.get(iso3)
    if iso2:
        if iso2 not in annual:
            annual[iso2] = {}
        annual[iso2]["citizen"] = val
        annual[iso2]["citizen_src"] = "WB_NETMIG"

# 샘플 출력
for iso2 in ["RU", "VE", "AR", "TR", "KR", "US", "JP"]:
    if iso2 in annual:
        print(f"  {iso2}: citizen={annual[iso2].get('citizen','?')}")


# ══════════════════════════════════════════════════════
# 5. 결과 저장
# ══════════════════════════════════════════════════════
data["annual"] = annual
data["_meta"]["last_annual_update"] = TODAY
data["_meta"]["annual_sources"] = {
    "law":     "World Bank WGI: Rule of Law (GOV_WGI_RL.SC, 0-100)",
    "demo":    "World Bank WGI: Voice & Accountability (GOV_WGI_VA.SC, 0-100)",
    "hd":      "BIS: Household credit / GDP % (WS_TC, quarterly)",
    "cd":      "BIS: Non-financial corp credit / GDP % (WS_TC, quarterly)",
    "dep3y":   "World Bank: Official exchange rate (PA.NUS.FCRF), 3-year change %",
    "citizen": "World Bank: Net migration (SM.POP.NETM), indexed 0-100",
}

with open("sentinel-data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 연간 지표 업데이트 완료: sentinel-data.json 저장됨")
print(f"   법치지수: {len(law_scores)}개국")
print(f"   민주주의지수: {len(demo_scores)}개국")
print(f"   가계부채: {hd_count}개국")
print(f"   기업부채: {cd_count}개국")
print(f"   3년 절하율: {len(dep3y_results)}개국")
print(f"   시민 탈출: {len(citizen_results)}개국")
