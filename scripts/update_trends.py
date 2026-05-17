#!/usr/bin/env python3
"""
SENTINEL Google Trends 자동 수집
GitHub Actions에서 주 1회 실행
25개국 × 4가지 키워드 유형 → sentinel-data.json 업데이트
"""

import json, time, os
from datetime import date
from pytrends.request import TrendReq

TODAY = str(date.today())

# ── 국가별 키워드 (현지어) ────────────────────────────────────────────────
# sell: 긴급현금화(전당포·금매도) — 임박 신호
# buy:  안전자산매수(금구매)     — 조기 경보
# flee: 시스템이탈(이민·계좌동결)— 구조적 불신
# bank: 뱅크런(예금인출)        — 은행취약 신호
KEYWORDS = {
    # ── 아시아 ────────────────────────────────────────────────────────────
    "KR": {"hl":"ko","sell":["전당포","금 팔기","귀금속 팔기"],
                      "buy":["금 사는법","금 시세 오늘"],
                      "flee":["계좌 동결","해외 이민","제2여권"],
                      "bank":["예금 인출","뱅크런","현금 인출"]},
    "JP": {"hl":"ja","sell":["質屋","金売る","金買取"],
                      "buy":["金投資","金の価格"],
                      "flee":["口座凍結","海外移住"],
                      "bank":["預金引き出し","取り付け騒ぎ"]},
    "IN": {"hl":"en","sell":["pawn shop","sell gold","gold buyer"],
                      "buy":["buy gold","gold price today"],
                      "flee":["emigrate India","second passport"],
                      "bank":["bank run India","withdraw deposit"]},
    "VN": {"hl":"vi","sell":["cầm đồ","bán vàng"],
                      "buy":["mua vàng","giá vàng"],
                      "flee":["phong tỏa tài khoản","di cư"],
                      "bank":["rút tiền ngân hàng"]},
    "ID": {"hl":"id","sell":["pegadaian","jual emas"],
                      "buy":["beli emas","harga emas"],
                      "flee":["pembekuan rekening","emigrasi"],
                      "bank":["rush bank","tarik uang"]},
    "PK": {"hl":"en","sell":["pawn shop Pakistan","sell gold"],
                      "buy":["buy gold Pakistan"],
                      "flee":["emigrate Pakistan"],
                      "bank":["bank run Pakistan"]},

    # ── 중동 ──────────────────────────────────────────────────────────────
    "TR": {"hl":"tr","sell":["rehinci","altın sat","altın bozdur"],
                      "buy":["altın al","altın fiyatı"],
                      "flee":["hesap dondurma","göç etmek"],
                      "bank":["bankadan para çekme","banka iflası"]},
    "IR": {"hl":"fa","sell":["گرو گذاشتن طلا","فروش طلا"],
                      "buy":["خرید طلا","قیمت طلا"],
                      "flee":["بلوکه شدن حساب","مهاجرت"],
                      "bank":["برداشت پول از بانک"]},
    "EG": {"hl":"ar","sell":["محل رهن","بيع الذهب"],
                      "buy":["شراء الذهب","سعر الذهب"],
                      "flee":["تجميد الحسابات","الهجرة"],
                      "bank":["سحب الودائع"]},
    "LB": {"hl":"ar","sell":["محل رهن","بيع الذهب"],
                      "buy":["شراء الذهب"],
                      "flee":["تجميد الحسابات","الهجرة"],
                      "bank":["سحب الودائع","بنك"]},

    # ── 아프리카 ──────────────────────────────────────────────────────────
    "NG": {"hl":"en","sell":["pawn shop","sell gold Nigeria","gold buyers"],
                      "buy":["buy gold Nigeria","gold price"],
                      "flee":["account freeze Nigeria","emigrate"],
                      "bank":["bank run Nigeria","withdraw money"]},
    "GH": {"hl":"en","sell":["pawn shop Ghana","sell gold"],
                      "buy":["buy gold Ghana"],
                      "flee":["account freeze Ghana"],
                      "bank":["bank run Ghana"]},
    "ZA": {"hl":"en","sell":["pawn shop","sell gold","cash for gold"],
                      "buy":["buy gold rand","krugerrand"],
                      "flee":["account freeze South Africa","emigrate"],
                      "bank":["bank run South Africa"]},
    "KE": {"hl":"en","sell":["pawn shop Kenya","sell gold"],
                      "buy":["buy gold Kenya"],
                      "flee":["account freeze Kenya"],
                      "bank":["bank run Kenya"]},

    # ── 유럽·CIS ──────────────────────────────────────────────────────────
    "TR": {"hl":"tr","sell":["rehinci","altın sat"],
                      "buy":["altın al","altın fiyatı"],
                      "flee":["hesap dondurma","göç etmek"],
                      "bank":["bankadan para çekme"]},
    "UA": {"hl":"uk","sell":["ломбард","продати золото"],
                      "buy":["купити золото","ціна золото"],
                      "flee":["заморожування рахунків","еміграція"],
                      "bank":["зняти гроші","банківський крах"]},
    "RU": {"hl":"ru","sell":["ломбард","сдать золото","продать золото"],
                      "buy":["купить золото","цена золота"],
                      "flee":["заморозка счетов","эмиграция"],
                      "bank":["снять деньги с банка","банкротство банка"]},

    # ── 아메리카 ──────────────────────────────────────────────────────────
    "AR": {"hl":"es","sell":["casa de empeño","vender oro","empeñar oro"],
                      "buy":["comprar oro","precio oro","dolar blue"],
                      "flee":["congelamiento cuentas","emigrar","corralito"],
                      "bank":["retirar dinero","banco quiebra"]},
    "VE": {"hl":"es","sell":["casa de empeño","vender oro"],
                      "buy":["comprar oro","dolar paralelo"],
                      "flee":["congelamiento cuentas","emigrar Venezuela"],
                      "bank":["retirar dinero banco"]},
    "BR": {"hl":"pt-BR","sell":["casa de penhores","vender ouro"],
                        "buy":["comprar ouro","preço do ouro"],
                        "flee":["congelamento contas","emigrar"],
                        "bank":["corrida bancária","sacar dinheiro"]},
    "CO": {"hl":"es","sell":["casa de empeño","vender oro"],
                      "buy":["comprar oro Colombia"],
                      "flee":["congelamiento cuentas Colombia"],
                      "bank":["retiro dinero banco"]},
}

# ── 수집 함수 ─────────────────────────────────────────────────────────────
def get_trend_score(pytrends, country, keywords, hl):
    """
    최근 3개월 평균 검색량 지수 반환 (0~100)
    pytrends의 interest_over_time()은 상대적 수치
    """
    try:
        # 키워드 최대 5개 (pytrends 제한)
        kw_list = keywords[:5]
        pytrends.build_payload(
            kw_list,
            geo=country,
            timeframe='today 3-m'
        )
        df = pytrends.interest_over_time()
        if df.empty:
            return None
        # 모든 키워드 평균
        score = df.drop(columns=['isPartial'], errors='ignore').mean().mean()
        return round(float(score), 1)
    except Exception as e:
        print(f"  ⚠️  {country} 트렌드 수집 실패: {e}")
        return None


# ── 메인 실행 ─────────────────────────────────────────────────────────────
with open("sentinel-data.json", encoding="utf-8") as f:
    data = json.load(f)

trends = data.get("trends", {})
print(f"📊 Google Trends 수집 시작 ({TODAY})")
print(f"   {len(KEYWORDS)}개국 × 4개 카테고리")
print("=" * 50)

pytrends = TrendReq(hl='en-US', tz=0, timeout=(10, 25))

for country, cfg in KEYWORDS.items():
    hl = cfg["hl"]
    country_trends = {}
    print(f"\n  {country} ({hl}):")

    for category in ["sell", "buy", "flee", "bank"]:
        keywords = cfg.get(category, [])
        if not keywords:
            continue
        score = get_trend_score(pytrends, country, keywords, hl)
        if score is not None:
            country_trends[category] = score
            emoji = "🔴" if score > 70 else "🟠" if score > 40 else "🟡"
            print(f"    {category}: {score} {emoji}")
        time.sleep(3)  # Rate limit 방지

    if country_trends:
        trends[country] = {
            **country_trends,
            "updated": TODAY
        }

data["trends"] = trends
data["_meta"]["last_trends_update"] = TODAY

with open("sentinel-data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 완료: {len(trends)}개국 트렌드 저장")

# 주목할 급등 국가 출력
print("\n🚨 주목 국가 (sell 지수 60+):")
for cid, t in sorted(trends.items(), key=lambda x: x[1].get("sell", 0), reverse=True):
    if t.get("sell", 0) >= 60:
        print(f"  {cid}: 전당포·금매도 {t['sell']} / 이민 {t.get('flee','-')} / 뱅크런 {t.get('bank','-')}")
