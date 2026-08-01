# Frontend TODO — COUNTER Dummy Evidence Memory

- 상태: P0–P2 반영 (2026-08-01)
- 기준: [`FRONTEND_ARCHITECTURE.md`](./FRONTEND_ARCHITECTURE.md)
- SoT: [`PRD.md`](./PRD.md) · [`ARCHITECTURE.md`](./ARCHITECTURE.md) · [`DECISIONS.md`](./DECISIONS.md)
- 코드: `apps/web`

현 단계: **evidence memory는 더미 데이터로 보이기만 한다.**  
실 DB/SSE/Streamlit 연동은 이 TODO 밖(제출 경로는 Streamlit).

---

## P0 — 도메인·카피를 COUNTER에 맞추기

- [x] `VerdictEnum` → `REFUTED` / `NOT_REFUTED` / `PUBLIC_SUBSTANTIATION_NOT_FOUND` / `PUFFERY`
- [x] `CacheDecision` → `HIT` / `MISS` / `DELTA` / `REVERIFY`
- [x] 이벤트 타입을 ARCHITECTURE §6 이름으로 교체
- [x] `EvidenceUnit` → `Candidate` (+ `applicability_check`, `passes_gate`)
- [x] 시나리오 스위처: `miss` / `hit` / `delta` / `puffery` / `scholar`
- [x] `NOT_REFUTED` 카피 가드
- [x] 신뢰도 % UI 없음
- [x] `PUFFERY` fixture: tool_call 0건

## P1 — 더미 시나리오·그래프 스토리

- [x] `miss`: triage → route → industry → cache MISS → LINER tools → candidates → verdict
- [x] `hit`: cache HIT → 재사용 candidate → 판정
- [x] `delta`: 재사용 dim → delta search → 새 candidate 강조
- [x] `puffery`: triage에서 종료
- [x] `scholar`: SCIENTIFIC + Scholar tool
- [x] Claim 캐시 링 / SearchRun pulse / Candidate→Verdict 엣지
- [x] provider(`liner`) 트레이스 배지

## P2 — UI 크롬

- [x] CacheStateBadge / VerdictAnswerPanel / SchemaTable COUNTER화
- [x] DetailDrawer: URL, published_at, applicability_check
- [x] Trace: 새 이벤트 요약 + active 하이라이트
- [ ] (선택) IMAGE/URL 입력 탭 비활성 껍데기

## P2.1 — 단일 페이지 유동 전환

- [ ] `hero` / `stage` 조건부 화면 교체를 영속적인 workspace shell로 변경
- [ ] idle 중앙 입력 → active 좌측 35% 입력 / 우측 65% 결과 전환
- [ ] 실행 중·완료 후에도 동일한 SearchBar 인스턴스와 입력값 유지
- [ ] 접힌 결과 패널을 `aria-hidden` + `inert`로 상호작용에서 제외
- [ ] 960px 이하에서 입력 위 / 결과 아래의 1열 레이아웃 제공
- [ ] `prefers-reduced-motion`에서 위치·크기 모션 제거
- [ ] `npm run lint`와 `npm run build` 통과

## P3 — 이후 (제출 / 실연동 — 이 단계 비범위)

- [ ] Streamlit 입력·결과·세컨드 raw poll·통계 페이지
- [ ] `DummyResearchClient` → 실 `trace_event` 어댑터(필요 시)
- [ ] 일시정지 / 한 스텝 리허설 컨트롤

---

## 완료 기준

- [x] 더미 재생이 COUNTER 이벤트·판정·캐시 enum을 쓴다
- [x] miss + puffery + (hit|delta)가 스위처로 구분된다
- [x] 그래프에 Claim→…→Candidate→Verdict 연결 성장이 보인다
- [x] D-02 / D-03 / N4 카피 가드 위반 없음
- [ ] 입력 후 새 페이지처럼 교체되지 않고 같은 셸에서 결과 패널이 열린다
