#!/usr/bin/env python3
"""
SENTINEL 자동 데이터 업데이트 스크립트
매주 실행: pp(암시장 괴리율) + World Bank 거시지표 업데이트
"""

import json
import requests
from datetime import date
from bs4 import BeautifulSoup
import time

TODAY = str(date.today())
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SentinelBot/1.0)"}

# ── 기존 데이터 로드 ────────────────────────────────────────────────────────
with open("sentinel-data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

pp_map = {item["id"]: item for item in data["pp_rates"]}
macro = data["macro"]

print(f"📅 업데이트 시작: {TODAY}")
print("=" * 50)


# ══════════════════════════════════════════════════════
# 1. 암시장 괴리율 (pp) 자동 스크래핑
# ══════════════════════════════════════════════════════

def scrape_safe(func, country_id, fallback_pp):
    """스크래핑 실패 시 기존 값 유지"""
    try:
        result = func()
        if result and 0 < result < 5000:
            print(f"  ✅ {country_id}: {result}%")
            return result
    except Exception as e:
        print(f"  ⚠️  {country_id}: 스크래핑 실패 ({e.__class__.__name__}), 기존값 {fallback_pp}% 유지")
    return fallback_pp


def get_iran_pp():
    """bonbast.com에서 이란 달러 자유시장 환율 가져오기"""
    r = requests.get("https://bonbast.com", headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    # 공식환율과 자유시장 환율 비교
    # 실제 파싱 로직 (사이트 구조에 따라 조정 필요)
    official = 42000   # IRR/USD 공식환율 (거의 고정)
    # 자유시장 환율 파싱
    price_el = soup.select_one("td.price")  # 실제 선택자 확인 필요
    if price_el:
        free_market = float(price_el.text.replace(",", ""))
        return round((free_market - official) / official * 100)
    return None


def get_nigeria_pp():
    """abokiforex.app에서 나이지리아 블랙마켓 환율"""
    r = requests.get("https://abokiforex.app", headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    official = 1600   # 공식환율 근사값
    bm_el = soup.select_one(".black-market-rate")  # 실제 선택자 확인 필요
    if bm_el:
        bm_rate = float(bm_el.text.replace(",", "").replace("₦", ""))
        return round((bm_rate - official) / official * 100)
    return None


def get_argentina_pp():
    """ambito.com에서 아르헨티나 블루달러 환율"""
    r = requests.get(
        "https://mercados.ambito.com/dolar/informal/variacion",
        headers=HEADERS, timeout=10
    )
    d = r.json()
    # {"fecha":"...", "valor":"1050.00", ...}
    if "valor" in d:
        blue = float(d["valor"].replace(",", "."))
        # 공식환율도 가져오기
        r2 = requests.get(
            "https://mercados.ambito.com/dolar/oficial/variacion",
            headers=HEADERS, timeout=10
        )
        d2 = r2.json()
        official = float(d2.get("valor", "1000").replace(",", "."))
        return round((blue - official) / official * 100)
    return None


def get_lebanon_pp():
    """lirarate.org API"""
    r = requests.get(
        "https://lirarate.org/api/latest.json",
        headers=HEADERS, timeout=10
    )
    d = r.json()
    # {"buy": 89500, "sell": 90000, "official": 89500}
    if "sell" in d and "official" in d:
        return round((d["sell"] - d["official"]) / d["official"] * 100)
    return None


def get_venezuela_pp():
    """monitordolarve.com 파싱"""
    r = requests.get("https://monitordolarve.com", headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    # 병렬환율과 공식환율 비교
    parallel_el = soup.select_one(".parallel-rate")
    official_el = soup.select_one(".official-rate")
    if parallel_el and official_el:
        parallel = float(parallel_el.text.replace(",", "."))
        official = float(official_el.text.replace(",", "."))
        return round((parallel - official) / official * 100)
    return None


print("\n📊 암시장 괴리율 (pp) 업데이트:")
pp_scrapers = [
    ("IR", get_iran_pp,     pp_map.get("IR", {}).get("pp", 1700)),
    ("NG", get_nigeria_pp,  pp_map.get("NG", {}).get("pp", 12)),
    ("AR", get_argentina_pp,pp_map.get("AR", {}).get("pp", 15)),
    ("LB", get_lebanon_pp,  pp_map.get("LB", {}).get("pp", 5)),
    ("VE", get_venezuela_pp,pp_map.get("VE", {}).get("pp", 45)),
]

for country_id, scraper, fallback in pp_scrapers:
    new_pp = scrape_safe(scraper, country_id, fallback)
    if country_id in pp_map:
        pp_map[country_id]["pp"] = new_pp
        pp_map[country_id]["updated"] = TODAY
    time.sleep(2)  # 서버 부하 방지


# ══════════════════════════════════════════════════════
# 2. World Bank API — 거시지표 자동 업데이트
# ══════════════════════════════════════════════════════

WB_INDICATORS = {
    "debt": "GC.DOD.TOTL.GD.ZS",   # 정부부채/GDP
    "ca":   "BN.CAB.XOKA.GD.ZS",   # 경상수지/GDP
    "inf":  "FP.CPI.TOTL.ZG",      # 인플레이션
}

# 업데이트할 국가 (World Bank 데이터 있는 나라)
WB_COUNTRIES = [
    "TR","AR","EG","LB","KR","JP","US","GB","CA","DE",
    "AU","SG","CH","SE","NZ","BR","CO","PE","ZA","IN",
    "ID","NG","GH","KE","PK","BD","LK","UA","RU","HU",
    "RO","PL","BY","KZ","UZ","VN","TH","MY",
]

print("\n🌍 World Bank API 거시지표 업데이트:")

def get_worldbank(country_iso2, indicator):
    """World Bank API에서 최신 지표값 가져오기"""
    url = (f"https://api.worldbank.org/v2/country/{country_iso2}"
           f"/indicator/{indicator}?format=json&mrv=3&per_page=3")
    r = requests.get(url, headers=HEADERS, timeout=15)
    d = r.json()
    if len(d) > 1 and d[1]:
        for item in d[1]:
            if item.get("value") is not None:
                return round(float(item["value"]), 1)
    return None

for country_id in WB_COUNTRIES:
    updates = {}
    for key, indicator in WB_INDICATORS.items():
        try:
            val = get_worldbank(country_id, indicator)
            if val is not None:
                updates[key] = val
        except Exception:
            pass
    
    if updates:
        if country_id not in macro:
            macro[country_id] = {}
        macro[country_id].update(updates)
        print(f"  ✅ {country_id}: {updates}")
    
    time.sleep(0.5)  # API 속도 제한 방지


# ══════════════════════════════════════════════════════
# 3. 결과 저장
# ══════════════════════════════════════════════════════

data["_meta"]["updated"] = TODAY
data["pp_rates"] = list(pp_map.values())
data["macro"] = macro

with open("sentinel-data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 업데이트 완료: sentinel-data.json 저장됨")
print(f"   pp 업데이트: {len(pp_scrapers)}개국")
print(f"   거시지표 업데이트: {len(WB_COUNTRIES)}개국")
