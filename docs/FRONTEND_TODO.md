# Frontend TODO — Live Graph Demo

- 상태: 오픈
- 날짜: 2026-08-01
- 기준 문서: [`FRONTEND_ARCHITECTURE.md`](./FRONTEND_ARCHITECTURE.md) §7 / §10
- 코드: `apps/web` (React Flow EvidenceGraph + DummyResearchClient 이벤트 재생)

이 문서는 **데모에서 “노드가 실시간으로 생기고 선으로 이어지는” 연출**을
완성하기 위한 프론트 TODO다. 백엔드/SSE 연동은 별도 항목으로만 적는다.

---

## 목표 (데모에서 한 눈에 보여야 하는 것)

검색 제출 후, 심사자가 설명 없이도 다음이 보여야 한다.

1. Claim 노드가 먼저 뜬다.
2. 캐시 판정 배지가 Claim 주변에 붙는다.
3. Scholar / Web SearchRun 노드가 생기고 Claim과 **선으로 연결**된다.
4. Source → EvidenceUnit이 순서대로 등장하며 상위 노드와 **엣지가 이어진다**.
5. Verdict 노드가 아래에 고정되고, 인용된 Evidence와 **강조 엣지**로 묶인다.
6. 이 과정이 한 번에 덤프되지 않고, 이벤트 타이밍에 맞춰 **실시간으로 성장**한다.

```text
Claim
  ├─(edge)→ SearchRun (Scholar) ──→ Source ──→ EvidenceUnit ──┐
  └─(edge)→ SearchRun (Web)      ──→ Source ──→ EvidenceUnit ──┴─→ Verdict
```

현재: reducer + `graph-mapper`로 노드/엣지 **데이터는** 이벤트마다 갱신된다.  
남은 일: 등장·연결·강조를 **시각적으로** 읽히게 만드는 것.

---

## P0 — 실시간 그래프 성장 (라이브 데모 핵심)

### P0-1. 이벤트 단위 노드 등장 모션

- [ ] 새 노드가 맵에 추가될 때 opacity / scale 짧은 entrance (약 200–350ms)
- [ ] Claim → SearchRun → Source → Evidence → Verdict 순서가 타이밍상 읽히게
  (`DummyResearchClient` step 간격과 맞춤, 기본 ~420ms)
- [ ] `prefers-reduced-motion`이면 transform 없이 opacity만

### P0-2. 엣지 “연결되는” 연출

- [ ] 노드가 생긴 직후 대응 엣지가 **그려지듯** 등장 (stroke draw / fade-in)
- [ ] `tool.call` 중 SearchRun 관련 엣지 `animated: true` (이미 일부 사용) 유지·확장
- [ ] Evidence → Verdict 엣지는 일반 엣지보다 strokeWidth / 색으로 한 단계 강조
- [ ] 한꺼번에 모든 선이 보이지 않고, 해당 이벤트 이후에만 보이게

### P0-3. 파이프라인 단계별 포커스

이벤트 → UI 하이라이트 매핑:

| 이벤트 | 그래프에서 보여 줄 것 |
| --- | --- |
| `claim.normalized` | Claim 노드 등장 + pulse |
| `cache.decision` | Claim 주변 캐시 링/배지 (`HIT_*` / `MISS` / `SEED_ONLY`) |
| `tool.call` | 해당 SearchRun 노드 pulse, Claim→SearchRun 엣지 animated |
| `tool.result` | SearchRun 안정화, Source 노드 준비 |
| `evidence.extracted` | Source + EvidenceUnit 등장, Source→Evidence 엣지 연결 |
| `verdict.updated` | Verdict 노드 고정, Evidence→Verdict 엣지 강조 |
| `job.completed` | 성장 모션 종료, 전체 fitView 한 번 |

- [ ] 위 매핑을 EvidenceGraph / node data에 `pulse` · `emphasis` 플래그로 반영
- [ ] 스테이지 전환 시 `fitView`가 성장 중 노드를 가리지 않게 (패딩·debounce)

### P0-4. HIT_STALE 전용 연결 스토리

- [ ] 재사용 Evidence/Source는 opacity 낮게 먼저 붙임
- [ ] delta 검색 후 **새** 노드만 하이라이트 + 새 엣지 강조
- [ ] stale → refreshed가 “선이 다시 살아나는” 느낌으로 읽히게

### P0-5. 시나리오별 연결 리허설 체크

- [ ] `MISS`: Claim → 양쪽 SearchRun → Sources → Evidences → Verdict 전체 성장
- [ ] `HIT_FRESH`: 검색 노드 최소, 재사용 Evidence가 Claim/Verdict로 바로 묶임
- [ ] `HIT_STALE`: 캐시 노드 dim → delta 노드/엣지 추가
- [ ] `SEED_ONLY`: seed Evidence만 연결되고 검색 경로가 짧게 보임

---

## P1 — 그래프와 나머지 UI 동기화

### P1-1. 선택 ↔ 연결 강조

- [ ] 노드/테이블 행 선택 시 해당 엔티티의 **인접 엣지**만 강조
- [ ] VerdictAnswer 인용 클릭 → Evidence 노드 + Claim↔Evidence 경로 하이라이트
- [ ] DetailDrawer 열릴 때 선택 노드가 뷰포트 안에 있도록 soft pan

### P1-2. Trace와 그래프 박자 맞추기

- [ ] AgentTracePanel 한 줄이 붙는 시점과 SearchRun/Evidence 등장 시점이 어긋나지 않게
- [ ] `tool.call` 줄 하이라이트 ↔ 그래프 SearchRun pulse 동기

### P1-3. SchemaTable “쌓이는” 연출

- [ ] 행이 이벤트마다 append될 때 짧은 row flash
- [ ] 그래프에서 연결된 엔티티와 같은 ID면 테이블 행도 동시 하이라이트

---

## P2 — 연출 품질 / 데모 안정성

### P2-1. React Flow UX

- [ ] 성장 중 자동 `fitView` debounce (과도한 줌 점프 방지)
- [ ] 노드 겹침 완화 (레이아웃 상수 또는 간단 dagre/ELK — 해커톤 범위에서 최소)
- [ ] Controls/미니맵은 데모 방해 안 되게 유지 (attribution 숨김 유지)

### P0과 겹치지 않는 모션 가드

아키텍처 §10 의도적 모션 3개만 지킨다.

1. Stage reveal (히어로 → 스테이지)
2. Graph growth (노드/엣지 실시간 연결) ← **이 TODO의 본체**
3. Stale refresh

- [ ] 파티클 / 과도한 glow / 보라 그라데이션 클리셰 추가하지 않기
- [ ] LAN IP 접속 시 HMR 차단으로 전환이 깨지지 않게 `allowedDevOrigins` 유지

### P2-2. 재생 컨트롤 (리허설용)

- [ ] step 간격 조절 (느리게 / 기본 / 빠르게) — 데모 리허설용
- [ ] (선택) 일시정지 / 한 스텝 — 심사 스크립트 연습용, 심사 UI에서는 숨김

---

## P3 — 이후 (실서버, 그래프 TODO와 분리)

- [ ] `HttpResearchClient` + SSE로 동일 reducer/mapper 유지
- [ ] 실이벤트 지연이 불규칙해도 그래프 성장이 어색하지 않게 (최소 간격 clamp)
- [ ] 프로덕션에서 `ScenarioSwitcher` 숨김 / 단축키만

---

## 완료 기준 (이 TODO 기준)

- [ ] MISS 시나리오에서 Claim→Search→Source→Evidence→Verdict가 **실시간으로 선이 이어지며** 보인다
- [ ] 엣지 없는 “노드만 툭툭” 쌓이는 느낌이 아니라, **연결 성장**으로 읽힌다
- [ ] Fresh / Stale / Miss 중 최소 두 시나리오에서 연결 스토리가 구분된다
- [ ] reduced-motion에서도 정보(등장 순서)는 유지된다

---

## 관련 파일

| 영역 | 경로 |
| --- | --- |
| 이벤트 재생 | `apps/web/lib/demo-scenarios.ts`, `research-client.ts` |
| 상태 적용 | `apps/web/lib/job-reducer.ts` |
| 노드/엣지 매핑 | `apps/web/lib/graph-mapper.ts` |
| 그래프 UI | `apps/web/components/EvidenceGraph.tsx` |
| 스테이지 전환 | `apps/web/components/DemoShell.tsx`, `app/globals.css` |
