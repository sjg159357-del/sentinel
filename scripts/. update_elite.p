#!/usr/bin/env python3
"""
SENTINEL Elite Exit Index v5.4
자산 이전 중심 키워드 + pytrends + GDELT + Bizjet
매주 일요일 2회 실행 (새벽 2시, 오후 2시)
"""

import json, requests, urllib.parse, time, sys
from datetime import date
from pytrends.request import TrendReq

try:
    import pycountry
except ImportError:
    pycountry = None

TODAY = str(date.today())
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SentinelElite/1.0)"}

def code_to_name(cc):
    name_map = {
        "KR":"South Korea","AR":"Argentina","TR":"Turkey","LB":"Lebanon",
        "VE":"Venezuela","EG":"Egypt","RU":"Russia","CN":"China","BR":"Brazil",
        "NG":"Nigeria","ET":"Ethiopia","GH":"Ghana","ZA":"South Africa",
        "IN":"India","IR":"Iran","MM":"Myanmar","BY":"Belarus","UA":"Ukraine",
        "PK":"Pakistan","SY":"Syria","IQ":"Iraq","SD":"Sudan","YE":"Yemen","ZW":"Zimbabwe"
    }
    if cc in name_map: return name_map[cc]
    if pycountry:
        try:
            c = pycountry.countries.get(alpha_2=cc)
            if c: return c.name.replace(", Republic of","").replace("Russian Federation","Russia")
        except: pass
    return cc

def get_trends_flee_score(country_code, retries=3):
    country_name = code_to_name(country_code)
    keywords = [
        f"offshore {country_name}",
        f"foreign account {country_name}",
        f"gold buying {country_name}",
        "second passport",
        "golden visa"
    ]
    for attempt in range(retries):
        try:
            pt = TrendReq(hl='en-US', tz=360, timeout=(10,25), retries=1)
            pt.build_payload(keywords, cat=0, timeframe='today 7-d', geo=country_code)
            df = pt.interest_over_time()
            if df.empty or len(df) < 2:
                return {"flee": 35, "spike": False}
            cols = [c for c in df.columns if c != 'isPartial']
            latest = df.iloc[-1][cols].mean()
            prev   = df.iloc[:-1][cols].mean().mean()
            return {"flee": int(round(latest)), "spike": bool(latest > prev * 1.4)}
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "rate limit" in err:
                wait = 70 * (attempt+1)
                print(f"  Rate limited ({country_code}), {wait}s 대기...")
                time.sleep(wait)
            else:
                print(f"  Trends Error {country_code}: {e}")
                if attempt == retries-1: return {"flee": 38, "spike": False}
                time.sleep(8)
    return {"flee": 38, "spike": False}

def get_gdelt_volume(country_name):
    try:
        q = f"({country_name}) (elite leaving OR capital flight OR wealthy fleeing OR offshore OR asset protection)"
        url = (f"https://api.gdeltproject.org/api/v2/doc/doc"
               f"?query={urllib.parse.quote(q)}&mode=artlist&format=json&timespan=7d&maxrecords=50")
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return min(100, len(r.json().get("articles",[])) * 3)
        return 32
    except Exception as e:
        print(f"  GDELT Error {country_name}: {e}")
        return 32

def calc_score(trends, bizjet, gdelt, country):
    t = trends.get(country,{}).get("flee",40)
    b = bizjet.get(country,{}).get("index",30)
    g = gdelt.get(country, 35)
    mult = 1.25 if trends.get(country,{}).get("spike",False) else 1.0
    return max(0, min(100, round((t*0.50 + b*0.25 + g*0.25) * mult)))

if __name__ == "__main__":
    with open("sentinel-data.json","r",encoding="utf-8") as f:
        data = json.load(f)

    print(f"🚀 Elite Exit Index v5.4 시작: {TODAY}")
    bizjet     = data.get("bizjet",{})
    trends_old = data.get("trends",{})
    countries  = sorted(set(list(trends_old.keys()) + list(bizjet.keys())))

    if not countries:
        print("⚠️ 국가 데이터 없음. bizjet/trends 먼저 실행 필요")
        sys.exit(0)  # exit(1) 대신 exit(0)으로 워크플로우 중단 방지

    trends_data, gdelt_data = {}, {}
    print(f"총 {len(countries)}개국")

    for i, country in enumerate(countries):
        print(f"[{i+1:2d}/{len(countries)}] {country}")
        trends_data[country] = get_trends_flee_score(country)
        gdelt_data[country]  = get_gdelt_volume(code_to_name(country))
        if (i+1) % 10 == 0 or (i+1) == len(countries):
            data["_checkpoint"] = {"trends":trends_data,"gdelt":gdelt_data,"processed":i+1}
            with open("sentinel-data.json","w",encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  💾 체크포인트 ({i+1}/{len(countries)})")
        time.sleep(2.3)

    elite_exit = {}
    for country in countries:
        score = calc_score(trends_data, bizjet, gdelt_data, country)
        elite_exit[country] = {
            "score": score,
            "trend_flee": trends_data.get(country,{}).get("flee"),
            "bizjet": bizjet.get(country,{}).get("index",0),
            "media": gdelt_data.get(country),
            "spike": trends_data.get(country,{}).get("spike",False),
            "updated": TODAY,
            "alert": score >= 70
        }

    data["elite_exit"] = elite_exit
    data.setdefault("_meta",{})["last_elite_update"] = TODAY
    data.pop("_checkpoint",None)

    with open("sentinel-data.json","w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 완료 ({len(elite_exit)}개국)")
    alerts = [c for c,v in elite_exit.items() if v["alert"]]
    if alerts: print(f"🚨 ALERT: {alerts}")
