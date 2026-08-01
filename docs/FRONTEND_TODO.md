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

- [x] `hero` / `stage` 조건부 화면 교체를 영속적인 workspace shell로 변경
- [x] idle 중앙 입력 → active 좌측 35% 입력 / 우측 65% 결과 전환
- [x] 실행 중·완료 후에도 동일한 SearchBar 인스턴스와 입력값 유지
- [x] 접힌 결과 패널을 `aria-hidden` + `inert`로 상호작용에서 제외
- [x] 960px 이하에서 입력 위 / 결과 아래의 1열 레이아웃 제공
- [x] `prefers-reduced-motion`에서 위치·크기 모션 제거
- [x] `npm run lint`와 `npm run build` 통과

## P2.2 — Experimental SearchBox → Claim node

- [x] submit/reset을 native View Transition으로 감싸고 미지원 fallback 제공
- [x] SearchBar와 Claim proxy/실제 Claim node에 shared-element 이름 인계
- [x] submit 직후 `model.query` 기반 optimistic `claim-1` node 렌더링
- [x] 실제 `claim.extracted`가 optimistic node ID를 그대로 이어받음
- [x] active 상태에서 SearchBar 제거, reset 시 역방향 morph
- [x] playback control 제거 및 `PLAYBACK_STEP_MS.slow` 고정
- [x] reduced-motion에서 이동·크기 morph 제거
- [x] 모바일 scroll anchoring 차단 및 시작 scroll 위치 복원
- [x] 데스크톱·모바일 실제 브라우저 렌더링 확인
- [x] `npm run lint`, TypeScript, `npm run build` 통과

## P2.3 — Experimental Active Answer Preview

- [x] active 전환 시 `COUNTER` wordmark를 왼쪽 패널 상단 reset anchor로 이동
- [x] 기존 wordmark 중심 위치에 `AnswerPreview` 배치
- [x] submitting/streaming 중 현재 파이프라인 단계 안내
- [x] verdict 조립 후 실제 `verdict` / `summary`로 preview 교체
- [x] failed/degraded 상태를 성공 결과와 구분
- [x] 좁은 화면과 reduced-motion에서 읽기 순서·전환 보장
- [x] `npm run lint`, TypeScript, `npm run build` 및 실제 브라우저 렌더링 확인

## P2.4 — Independent Category Memory Pyramid

- [x] `/database` 독립 route 진입 즉시 category explorer 렌더
- [x] 원격 main seed의 13개 업종 + `UNCATEGORIZED`를 stable node로 표현
- [x] category 선택 시 실제 centroid phrase level을 아래로 펼침
- [x] phrase 선택 시 keyword level을 아래로 펼침
- [x] 선택 경로 중앙축 + 형제 node fan으로 수직 피라미드 구성
- [x] 신규 level node를 stagger cascade animation으로 등장
- [x] 평면 DB의 시각적 projection이며 FK hierarchy가 아님을 명시
- [x] 모바일·키보드 탐색과 `prefers-reduced-motion` fallback 제공
- [x] `npm run lint`, TypeScript, `npm run build` 및 실제 브라우저 렌더링 확인

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
- [x] 입력 후 새 페이지처럼 교체되지 않고 같은 셸에서 결과 패널이 열린다
- [x] 검색창 box가 그래프 Claim node로 직접 transform된다
