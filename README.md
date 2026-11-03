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


## 2026-11 자동화 안정성 패치

- `.github/workflows/update.yml` 및 `update-elite.yml`이 동일한 `concurrency` 그룹을 사용해 데이터 파일 동시 갱신을 제한합니다.
- Elite 작업의 `--force-with-lease` Push를 제거하고, 두 워크플로 모두 원격 `main`을 `fetch`/`rebase`한 뒤 일반 Push합니다.
- 원격 데이터와 충돌하면 GitHub Actions는 실패 상태로 멈춥니다. **자동 강제 덮어쓰기는 하지 않습니다.** 수동 커밋과 겹치는 경우 충돌을 확인해야 합니다.
- 최근 실시간 알림이 오래된 알림에 밀려 삭제되는 목록 절단 오류를 수정했습니다.
- OpenSky API 오류나 빈 응답 시 기존 비즈니스 제트 데이터를 지우지 않게 했습니다.
- 실제 외부 API 수집과 GitHub Actions 실행은 로컬 정적 점검만으로 검증할 수 없습니다.

### 적용 방법

ZIP 전체를 기존 GitHub 저장소에 반영하거나 변경된 5개 파일만 교체하세요. 기존 `sentinel-data.json`을 수정하지 않았으며, 저장소에 새로운 자동 수집 결과가 있다면 **기존 JSON 파일을 덮어쓰지 마세요.** GitHub Actions의 `Actions` 탭에서 `workflow_dispatch`로 실행 결과를 확인하세요.

