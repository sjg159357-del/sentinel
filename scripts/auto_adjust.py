#!/usr/bin/env python3
"""
SENTINEL 뉴스 기반 자동 점수 조정
특정 키워드 뉴스 감지 시 → sentinel-data.json에 조정값 반영
"""

import json, requests, re, os
from datetime import date

TODAY = str(date.today())
HEADERS = {"User-Agent": "Mozilla/5.0 (SentinelBot/1.0)"}

with open("sentinel-data.json", encoding="utf-8") as f:
    data = json.load(f)

adjustments = data.get("adjustments", {})
alerts = data.get("alerts", [])
new_adjustments = []

# ── 자동 조정 트리거 규칙 ─────────────────────────────────────────────────
# 뉴스에서 특정 패턴 감지 시 해당 국가 점수 조정

TRIGGERS = [
    # (검색 키워드, 국가코드, 조정 필드, 조정값, 설명)
    ("South Africa crypto law passed seizure",    "ZA", "hist", +1, "ZA 암호화폐 압수법 통과"),
    ("France crypto wallet ban",                  "FR", "hist", +1, "프랑스 개인지갑 금지"),
    ("EU personal wallet ban crypto",             "DE", "hist", +1, "EU 개인지갑 금지 독일 적용"),
    ("China crypto arrest seizure",               "CN", "citizen", +3, "중국 암호화폐 탄압 강화"),
    ("Nigeria capital controls forex",            "NG", "hist", +1, "나이지리아 자본통제"),
    ("India capital controls account freeze",     "IN", "hist", +1, "인도 자본통제"),
    ("Turkey capital controls lira",              "TR", "hist", +1, "터키 자본통제"),
    ("Argentina bank account freeze corralito",   "AR", "hist", +1, "아르헨티나 계좌동결"),
    ("IMF bailout capital controls",              None, None,    0, "IMF 구제금융"),  # 국가별 처리
]

print(f"📊 뉴스 기반 자동 점수 조정 ({TODAY})")
print("="*55)

def search_gdelt(query, days=7):
    """GDELT에서 최근 뉴스 검색"""
    try:
        from datetime import timedelta
        start = (date.today() - timedelta(days=days)).strftime("%Y%m%d") + "000000"
        end = date.today().strftime("%Y%m%d") + "235959"
        url = (
            f"https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={requests.utils.quote(query)}"
            f"&mode=artlist&maxrecords=5&format=json"
            f"&startdatetime={start}&enddatetime={end}"
        )
        r = requests.get(url, headers=HEADERS, timeout=15)
        articles = r.json().get("articles", [])
        return articles
    except:
        return []

# ── 트리거별 뉴스 검색 및 조정 적용 ─────────────────────────────────────
for query, country_id, field, delta, label in TRIGGERS:
    articles = search_gdelt(query, days=3)
    if not articles:
        continue
    
    print(f"\n🔍 '{label}' 감지:")
    for art in articles[:2]:
        print(f"  - {art.get('title','')[:60]}")
    
    if country_id and field:
        # 조정 기록
        adj_key = f"{country_id}_{field}"
        existing = adjustments.get(adj_key, {})
        
        # 최근 7일 내 이미 조정됐으면 중복 적용 안 함
        last_adj = existing.get("date", "2000-01-01")
        if last_adj >= TODAY:
            print(f"  → {country_id} {field} 이미 조정됨 (건너뜀)")
            continue
        
        old_val = existing.get("value", 0)
        new_val = min(3, old_val + delta)  # hist max=3
        
        adjustments[adj_key] = {
            "country": country_id,
            "field": field,
            "delta": delta,
            "value": new_val,
            "reason": label,
            "date": TODAY,
            "source": articles[0].get("url",""),
            "requires_review": True  # 사람 검토 후 sentinel.html 반영
        }
        new_adjustments.append(adjustments[adj_key])
        
        alert = {
            "type": "점수조정",
            "country": country_id,
            "message": f"📊 {country_id} {field} +{delta} 조정 권장: {label}",
            "date": TODAY,
            "requires_review": True,
            "adjustment": adjustments[adj_key]
        }
        alerts.append(alert)
        print(f"  → {country_id} {field}: {old_val} → {new_val} (검토 필요)")

# ── 결과 저장 ─────────────────────────────────────────────────────────────
data["adjustments"] = adjustments
data["alerts"] = alerts[-30:]  # 최근 30개 유지
data["_meta"]["last_adjustment_check"] = TODAY

with open("sentinel-data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 완료: {len(new_adjustments)}개 조정 제안")
print("⚠️  모든 조정은 'requires_review:true' — 사람 검토 후 sentinel.html 반영 필요")
