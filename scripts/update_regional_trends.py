#!/usr/bin/env python3
"""
SENTINEL 지역별 위기 키워드 트렌드 업데이트
주 1회 실행 (GitHub Actions)

Yandex/Baidu 대체 방안:
  - Yandex 검색 트렌드 → Google Trends RU 지역 (러시아어 키워드)
  - Baidu 검색 트렌드  → Google Trends CN 지역 (중국어 키워드)
  - 이란, 터키 등 추가 지역도 동일 방식으로 수집

한계:
  - Google Trends는 중국/러시아 내부에서 차단되지만,
    외부에서 해당 지역 데이터를 조회하는 것은 가능
  - Yandex 고유 검색 데이터(Wordstat)와 완전히 동일하지 않음
  - 중국(CN)은 Google 사용률이 낮아 데이터 신뢰도 제한적
  - API 속도 제한(429)으로 실패 시 이전 데이터 유지

국가별 위기 키워드:
  RU: кризис (crisis), инфляция (inflation), девальвация (devaluation)
  CN: 经济危机 (economic crisis), 通货膨胀 (inflation), 货币贬值 (devaluation)
  TR: ekonomik kriz, enflasyon, döviz krizi
  IR: بحران اقتصادی (economic crisis), تورم (inflation)
  AR: crisis economica, inflacion, devaluacion
  VE: crisis economica, hiperinflacion, dolarizacion
"""

import json
import time
from datetime import date

TODAY = str(date.today())

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    print("⚠️  pytrends 미설치. pip install pytrends")

print(f"📈 지역별 위기 키워드 트렌드 업데이트 시작: {TODAY}")
print("=" * 60)

# ── 기존 데이터 로드 ────────────────────────────────────────────────────────
with open("sentinel-data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

if "regional_trends" not in data:
    data["regional_trends"] = {}

# ── 지역별 키워드 정의 ──────────────────────────────────────────────────────
REGIONAL_KEYWORDS = {
    "RU": {
        "geo": "RU",
        "hl": "ru",
        "tz": 180,
        "keywords": ["кризис", "инфляция", "девальвация"],
        "label": "러시아 (Google Trends RU, Yandex 대체)"
    },
    "CN": {
        "geo": "CN",
        "hl": "zh-CN",
        "tz": 480,
        "keywords": ["经济危机", "通货膨胀", "货币贬值"],
        "label": "중국 (Google Trends CN, Baidu 대체, 신뢰도 제한)"
    },
    "TR": {
        "geo": "TR",
        "hl": "tr",
        "tz": 180,
        "keywords": ["ekonomik kriz", "enflasyon", "döviz krizi"],
        "label": "터키 (Google Trends TR)"
    },
    "IR": {
        "geo": "IR",
        "hl": "fa",
        "tz": 210,
        "keywords": ["بحران اقتصادی", "تورم", "ریزش بورس"],
        "label": "이란 (Google Trends IR)"
    },
    "AR": {
        "geo": "AR",
        "hl": "es",
        "tz": -180,
        "keywords": ["crisis economica", "inflacion", "devaluacion"],
        "label": "아르헨티나 (Google Trends AR)"
    },
    "VE": {
        "geo": "VE",
        "hl": "es",
        "tz": -240,
        "keywords": ["crisis economica", "hiperinflacion", "dolarizacion"],
        "label": "베네수엘라 (Google Trends VE)"
    },
    "ZW": {
        "geo": "ZW",
        "hl": "en",
        "tz": 120,
        "keywords": ["economic crisis", "inflation", "currency collapse"],
        "label": "짐바브웨 (Google Trends ZW)"
    },
    "MM": {
        "geo": "MM",
        "hl": "my",
        "tz": 390,
        "keywords": ["ငွေကြေးဖောင်းပွမှု", "စီးပွားရေးကပ်ဆိုး", "kyat devaluation"],
        "label": "미얀마 (Google Trends MM)"
    },
}

if not PYTRENDS_AVAILABLE:
    print("❌ pytrends 없어서 건너뜀")
else:
    success_count = 0
    fail_count = 0

    for iso2, config in REGIONAL_KEYWORDS.items():
        print(f"\n  [{iso2}] {config['label']}")
        try:
            pytrends = TrendReq(
                hl=config["hl"],
                tz=config["tz"],
                timeout=(10, 30),
                retries=2,
                backoff_factor=0.5
            )

            # 키워드별 최근 3개월 트렌드 수집
            keyword_scores = {}
            for kw in config["keywords"]:
                try:
                    pytrends.build_payload(
                        [kw],
                        cat=0,
                        timeframe="today 3-m",
                        geo=config["geo"],
                        gprop=""
                    )
                    df = pytrends.interest_over_time()
                    if not df.empty and kw in df.columns:
                        # 최근 4주 평균
                        recent_avg = float(df[kw].tail(4).mean())
                        # 3개월 전 4주 평균
                        baseline_avg = float(df[kw].head(4).mean())
                        keyword_scores[kw] = {
                            "recent_avg": round(recent_avg, 1),
                            "baseline_avg": round(baseline_avg, 1),
                            # 상승률: 양수=위기 관심 증가
                            "change_pct": round(
                                (recent_avg - baseline_avg) / max(baseline_avg, 1) * 100, 1
                            )
                        }
                        print(f"    {kw}: 최근={recent_avg:.1f}, 기준={baseline_avg:.1f}, 변화={keyword_scores[kw]['change_pct']:+.1f}%")
                    else:
                        print(f"    {kw}: 데이터 없음 (0)")
                        keyword_scores[kw] = {"recent_avg": 0, "baseline_avg": 0, "change_pct": 0}
                    
                    time.sleep(3)  # 속도 제한 방지

                except Exception as e:
                    print(f"    {kw}: 실패 ({e})")
                    keyword_scores[kw] = {"recent_avg": 0, "baseline_avg": 0, "change_pct": 0}
                    time.sleep(5)

            # 국가 종합 점수: 키워드별 change_pct 평균
            avg_change = sum(
                v["change_pct"] for v in keyword_scores.values()
            ) / max(len(keyword_scores), 1)

            data["regional_trends"][iso2] = {
                "keywords": keyword_scores,
                "avg_change_pct": round(avg_change, 1),
                "updated": TODAY,
                "source": "Google Trends (Yandex/Baidu 대체)" if iso2 in ("RU", "CN") else "Google Trends",
                "note": config["label"]
            }
            success_count += 1

        except Exception as e:
            print(f"    ❌ {iso2} 전체 실패: {e}")
            fail_count += 1
            time.sleep(10)

    print(f"\n  완료: 성공 {success_count}개국, 실패 {fail_count}개국")

# ── sentinel-data.json 저장 ──────────────────────────────────────────────────
data["_meta"]["last_regional_trends_update"] = TODAY

with open("sentinel-data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 지역별 트렌드 업데이트 완료")
print(f"   sentinel-data.json 저장됨")
