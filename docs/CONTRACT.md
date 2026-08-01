# Frontend ↔ Backend Contract

- 상태: 초안 (해커톤 MVP)
- 날짜: 2026-08-01
- 관련: [`SERVICE_ARCHITECTURE.md`](./SERVICE_ARCHITECTURE.md) §8, [`FRONTEND_ARCHITECTURE.md`](./FRONTEND_ARCHITECTURE.md) §4–6
- 코드 미러: [`apps/web/types/events.ts`](../apps/web/types/events.ts), [`apps/web/types/domain.ts`](../apps/web/types/domain.ts)

이 문서는 **웹 UI와 application API 사이의 유일한 통신 계약**이다.
정책·오케스트레이션 의미는 서비스 아키텍처가 소유하고, 이 문서는
엔드포인트·요청/응답·SSE 이벤트 shape만 고정한다.

변경 시: 이 문서 → 프론트 타입 → (이후) 백엔드 스키마 순으로 맞춘다.

---

## 1. 범위

### In scope

| 방향 | 무엇 |
| --- | --- |
| Client → API | research job 생성 |
| API → Client | job 스냅샷 조회, SSE 트레이스, source 메타데이터 |

### Out of scope

- DB 직접 접근
- Liner / OpenAI 등 provider 직접 호출 (서버 전용)
- API 키·authorization 헤더를 브라우저에 노출
- 인증/멀티테넌트 UI (MVP 이후)

Wire format: JSON (`Content-Type: application/json`).  
SSE: `text/event-stream`, 각 `data:` 줄은 아래 `ResearchEvent` JSON 한 건.

---

## 2. 공유 enum

```text
JobStatus
  queued | running | complete | degraded | failed

CacheDecision
  HIT_FRESH | HIT_STALE | SEED_ONLY | MISS | INVALID

Verdict
  Direct | Partial | Mixed | Not found

AccessLevel
  metadata | snippet | abstract | full_text

EvidenceRelation
  direct | broader | narrower | conflicting | unrelated

EvidenceDirection
  supports | refutes | mixed | background
```

문자열은 대소문자·띄어쓰기를 **표와 동일하게** 쓴다 (`Not found` 포함).

---

## 3. HTTP 엔드포인트

베이스 URL은 환경변수로 둔다 (예: `NEXT_PUBLIC_API_BASE_URL`).  
프리픽스: `/v1`.

### 3.1 `POST /v1/research`

질문 하나로 research job을 만든다. **클라이언트의 유일한 write.**

**Request**

```json
{
  "query": "string, required, non-empty"
}
```

**Response `201`**

```json
{
  "job_id": "string"
}
```

**Errors**

| HTTP | 언제 |
| --- | --- |
| `400` | `query` 누락/공백 |
| `429` | single-flight 또는 rate limit (가능하면 기존 `job_id` 안내) |
| `500` | 서버 오류 |

클라이언트의 다음 동작: `job_id`로 §3.3 SSE를 구독한다.

---

### 3.2 `GET /v1/research/{job_id}`

현재 구조화 스냅샷. SSE 재연결·새로고침 보강용.

**Response `200`**

```json
{
  "job_id": "string",
  "query": "string",
  "status": "queued | running | complete | degraded | failed",
  "cache_decision": "HIT_FRESH | … | null",
  "verdict": "Direct | Partial | Mixed | Not found | null",
  "answer": "string | null",
  "citation_evidence_ids": ["string"],
  "reason_codes": ["string"],
  "error": { "code": "string", "message": "string" } | null,
  "updated_at": "ISO-8601"
}
```

선택 필드(`cache_decision`, `verdict`, `answer` 등)는 job 진행 중 `null`일 수 있다.

**Errors:** `404` unknown job.

---

### 3.3 `GET /v1/research/{job_id}/events`

라이브 트레이스 SSE.

**Headers (응답)**

```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**이벤트 프레임**

```text
id: <sequence>
event: <ResearchEventType>
data: <ResearchEvent JSON>

```

- `id`는 `sequence`와 같게 두는 것을 권장 (Last-Event-ID 재연결용).
- 스트림은 `job.completed` 또는 `job.failed` 이후 서버가 닫는다.
- 동일 `claim_key` miss의 single-flight 시, 후속 클라이언트는 **새 검색 없이** 기존 job 스트림을 구독할 수 있다.

**Errors:** `404` before stream starts.

---

### 3.4 `GET /v1/sources/{source_id}`

evidence 카드/디테일 보강 (MVP에서 optional; 없어도 SSE `evidence.extracted`만으로 데모 가능).

**Response `200`**

```json
{
  "source_id": "string",
  "title": "string",
  "url": "string | null",
  "publisher": "string | null",
  "publication_date": "string | null",
  "access_level": "metadata | snippet | abstract | full_text",
  "excerpt_or_summary": "string",
  "captured_at": "ISO-8601 | null"
}
```

**Errors:** `404`.

---

## 4. SSE `ResearchEvent`

모든 이벤트 공통 envelope:

```json
{
  "job_id": "string",
  "sequence": 1,
  "type": "job.created",
  "created_at": "ISO-8601",
  "payload": {}
}
```

규칙:

- `sequence`는 job 내 단조 증가 정수 (1부터).
- `created_at`은 UTC ISO-8601.
- `payload`에는 **마스킹된 public 데이터만**. 금지: API 키, authorization, 과도한 raw 페이지 텍스트, 다른 tenant의 raw 쿼리.
- 알 수 없는 `type`은 클라이언트가 skip (스트림은 유지).
- 파싱 실패 한 건은 skip; endless spinner 금지.

### 4.1 이벤트 목록

| `type` | `payload` | 비고 |
| --- | --- | --- |
| `job.created` | `{ "status": "running" }` | 구독 직후 |
| `claim.normalized` | `{ "claim_id", "signature_summary" }` | UI Claim 노드 |
| `cache.candidate` | `{ "candidate_claim_ids": [], "scores"?: number[] }` | |
| `cache.decision` | `{ "decision": CacheDecision, "reused_evidence_count"?: number, "reason_codes"?: string[] }` | |
| `tool.call` | `{ "tool_name", "agent_label", "args_redacted", "search_run_id"? }` | Scholar/Web |
| `tool.result` | `{ "tool_name", "ok", "result_summary", "provider_request_id"?, "search_run_id"? }` | Liner는 앱이 wrap |
| `evidence.extracted` | `EvidenceUnit` (§5) | 누적 append |
| `verdict.updated` | `{ "verdict": Verdict, "evidence_ids": [], "reason_codes"? }` | 최종 전 갱신 가능 |
| `answer.delta` | `{ "text_delta", "citation_evidence_ids"? }` | 누적 연결 |
| `job.completed` | `{ "status": "complete" \| "degraded" }` | 터미널 |
| `job.failed` | `{ "error_code", "message" }` | 터미널 |

권장 `tool_name`: `scholar_search`, `web_search`.  
권장 `agent_label`: `Scholar Agent`, `Web Agent` (UI 라벨용; 백엔드 권한과 무관).

### 4.2 TypeScript 유니온 (규범)

프론트 구현과 동일. 백엔드 직렬화도 이 shape를 따른다.

```ts
type ResearchEventType =
  | "job.created"
  | "claim.normalized"
  | "cache.candidate"
  | "cache.decision"
  | "tool.call"
  | "tool.result"
  | "evidence.extracted"
  | "verdict.updated"
  | "answer.delta"
  | "job.completed"
  | "job.failed";

type ResearchEvent =
  | { type: "job.created"; job_id: string; sequence: number; created_at: string;
      payload: { status: string } }
  | { type: "claim.normalized"; job_id: string; sequence: number; created_at: string;
      payload: { claim_id: string; signature_summary: string } }
  | { type: "cache.candidate"; job_id: string; sequence: number; created_at: string;
      payload: { candidate_claim_ids: string[]; scores?: number[] } }
  | { type: "cache.decision"; job_id: string; sequence: number; created_at: string;
      payload: {
        decision: "HIT_FRESH" | "HIT_STALE" | "SEED_ONLY" | "MISS" | "INVALID";
        reused_evidence_count?: number;
        reason_codes?: string[];
      } }
  | { type: "tool.call"; job_id: string; sequence: number; created_at: string;
      payload: {
        tool_name: string;
        agent_label: string;
        args_redacted: Record<string, unknown>;
        search_run_id?: string;
      } }
  | { type: "tool.result"; job_id: string; sequence: number; created_at: string;
      payload: {
        tool_name: string;
        ok: boolean;
        result_summary: string;
        provider_request_id?: string;
        search_run_id?: string;
      } }
  | { type: "evidence.extracted"; job_id: string; sequence: number; created_at: string;
      payload: EvidenceUnit }
  | { type: "verdict.updated"; job_id: string; sequence: number; created_at: string;
      payload: {
        verdict: "Direct" | "Partial" | "Mixed" | "Not found";
        evidence_ids: string[];
        reason_codes?: string[];
      } }
  | { type: "answer.delta"; job_id: string; sequence: number; created_at: string;
      payload: { text_delta: string; citation_evidence_ids?: string[] } }
  | { type: "job.completed"; job_id: string; sequence: number; created_at: string;
      payload: { status: "complete" | "degraded" } }
  | { type: "job.failed"; job_id: string; sequence: number; created_at: string;
      payload: { error_code: string; message: string } };
```

---

## 5. `EvidenceUnit` (SSE / UI 투영)

서비스 도메인 `EvidenceUnit`의 **클라이언트 안전 투영**.  
`access_level`은 생략 금지.

```json
{
  "evidence_id": "string",
  "claim_id": "string",
  "source_snapshot_id": "string",
  "source_id": "string | optional",
  "title": "string | optional",
  "url": "string | optional",
  "access_level": "metadata | snippet | abstract | full_text",
  "relation": "direct | broader | narrower | conflicting | unrelated",
  "direction": "supports | refutes | mixed | background",
  "matched_scope": { "subject": "…", "outcome": "…" },
  "missing_scope": ["string"],
  "excerpt_or_summary": "string",
  "extracted_at": "ISO-8601"
}
```

인용 URL(`url`)이 있으면 UI는 클릭 가능한 링크로 렌더한다.

---

## 6. 클라이언트 어댑터 계약

UI는 HTTP를 직접 흩뿌리지 않고 `ResearchClient` 뒤로 숨긴다.

```ts
interface ResearchClient {
  createJob(input: { query: string }): Promise<{ job_id: string }>;
  getJob(jobId: string): Promise<JobSnapshot>;
  subscribeEvents(
    jobId: string,
    onEvent: (event: ResearchEvent) => void,
  ): () => void; // unsubscribe
}
```

| 구현 | 역할 |
| --- | --- |
| `DummyResearchClient` | fixture 타이머 재생 (현재 데모) |
| `HttpResearchClient` | §3 HTTP + SSE (연동 시) |

`scenarioHint` 등은 **데모 전용**이며 production API request에 넣지 않는다.

---

## 7. 전형적 시퀀스

```text
Client                     API
  |-- POST /v1/research -->|
  |<- { job_id } ----------|
  |-- GET .../events ----->|  (SSE)
  |<- job.created ---------|
  |<- claim.normalized ----|
  |<- cache.* -------------|
  |<- tool.call/result ----|  (0..n, MISS/STALE 등)
  |<- evidence.extracted --|  (0..n)
  |<- verdict.updated -----|
  |<- answer.delta --------|  (0..n)
  |<- job.completed/failed-|
  |      (stream close)    |
```

`HIT_FRESH`에서는 `tool.*`가 거의 없고, 재사용 evidence + 새 answer가 나올 수 있다.  
`HIT_STALE`에서는 캐시 evidence가 먼저 보이고 delta `tool.*` 후 교체된다.

---

## 8. 오류·강건성

| 상황 | 계약 |
| --- | --- |
| Provider 부분 실패 | `job.completed` + `status: "degraded"` 가능; endless running 금지 |
| 전체 실패 | `job.failed` + public `message` |
| SSE 끊김 | 클라이언트는 `GET /v1/research/{id}`로 스냅샷 보강 후, 가능하면 `Last-Event-ID`로 재구독 |
| 알 수 없는 이벤트 | skip |
| 마스킹 | raw private query 전문·secrets는 이벤트에 없음 |

---

## 9. 버전

- 현재 wire 버전: **v1** (URL prefix).
- 하위 호환이 깨지는 필드 변경은 `/v2` 또는 명시적 `contract_version` 필드로 올린다.
- OpenAPI 산출물이 생기면 이 문서의 §3–5를 생성 소스로 삼거나, OpenAPI를 SoT로 승격하고 여기를 요약본으로 강등한다.
