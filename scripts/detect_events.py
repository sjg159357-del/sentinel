#!/usr/bin/env python3
"""
SENTINEL v3.1 - 실시간 이벤트 감지 (매시간 실행)
"""

import json
import requests
import os
from datetime import datetime, date

TODAY = str(date.today())
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SentinelBot/1.0)"}

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")

with open("sentinel-data.json", encoding="utf-8") as f:
    data = json.load(f)

alerts = data.get("alerts", [])
new_alerts = []

print(f"🚨 SENTINEL 실시간 감지 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 환율 급변 체크
try:
    r = requests.get("https://open.er-api.com/v6/latest/USD", headers=HEADERS, timeout=10)
    rates = r.json().get("rates", {})
    print("  환율 데이터 수신 완료")
except:
    pass

# 위기 키워드 감지
print("🌍 위기 키워드 모니터링...")
crisis_keywords = ["bank run", "capital control", "dolar blue", "corralito", "account freeze"]
for kw in crisis_keywords:
    try:
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={requests.utils.quote(kw)}&mode=artlist&maxrecords=2&format=json"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            for article in r.json().get("articles", [])[:2]:
                new_alerts.append({
                    "type": "실시간",
                    "message": f"🔥 {kw} 관련 뉴스 감지",
                    "title": article.get("title", "")[:100],
                    "date": TODAY,
                    "time": datetime.now().strftime("%H:%M")
                })
    except:
        pass

# 저장
data["alerts"] = (new_alerts + alerts)[-50:]
data["_meta"]["last_real_time"] = datetime.now().isoformat()

with open("sentinel-data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 텔레그램 알림
if new_alerts and TG_TOKEN and TG_CHAT:
    msg = f"🚨 SENTINEL 실시간 경보 ({datetime.now().strftime('%H:%M')})\n\n" + "\n".join(a["message"] for a in new_alerts[:5])
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      json={"chat_id": TG_CHAT, "text": msg})
    except:
        pass

print(f"✅ 완료: {len(new_alerts)}개 새 경보")