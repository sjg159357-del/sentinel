# SENTINEL v4 Final · 글로벌 자산 몰수·동결 조기경보

## 이번 버전 = 통합본(v3.1) + Claude v4 수정사항 합본

### Claude v4에서 수정한 핵심 버그
1. dep = max(1년절하율, dep3y÷3) — 일본·한국·레바논 환율신호 0점 문제 수정
2. 네이버 DataLab URL 수정 (GET 미지원 → 검색 URL)
3. 외환통제 국가 이상감지 경보 추가
4. 검색트렌드 신뢰도 낮은 국가 경보 (레바논·시리아 등)

### Manus+Grok(통합본)에서 추가한 기능
1. update_annual.py — 법치·민주·가계부채·기업부채 API 자동화
2. update_bizjet.py — OpenSky 비즈니스제트 추적
3. update_regional_trends.py — 비구글 국가 트렌드 우회 수집
4. annual 섹션 동적 로드

## 파일 구조
sentinel-final-v4/
├── sentinel.html
├── sentinel-data.json
├── scripts/
│   ├── update_data.py           주 1회: pp + World Bank
│   ├── detect_events.py         매일: 환율급변·IMF·뉴스
│   ├── update_trends.py         주 1회: Google Trends
│   ├── update_annual.py         연 1회: 법치·민주·부채 자동화 (NEW)
│   ├── update_bizjet.py         주 1회: 비즈니스제트 추적 (NEW)
│   └── update_regional_trends.py 주 1회: 지역별 트렌드 (NEW)
└── .github/workflows/update.yml

⚠️ 추정치 포함. 투자·이민 결정 단독 근거 사용 금지.
