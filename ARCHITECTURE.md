# COUNTER — Architecture

> 전제: `PRD.md`를 먼저 읽었을 것. 특히 §4 불가침 규칙.

---

## 0. 설계 원칙

이 대회의 Pipeline Architecture 배점(25%)은 **"각 도구 호출이 왜 그 순서인가"**를 봅니다. 따라서 각 단계는 다음 두 질문에 답할 수 있어야 합니다.

1. 이 단계가 **왜 이 위치**에 있는가?
2. 이 단계를 **앞이나 뒤로 옮기면 무엇이 깨지는가**?

각 단계 설명에 그 답을 함께 적어뒀습니다. 코드 주석에도 남기세요 — 심사위원이 저장소를 봅니다.

핵심 구조 원칙: **오케스트레이션은 애플리케이션이 소유하고, LLM은 각 단계 안에서만 판단한다.** LLM이 "다음에 뭘 할지"를 자유롭게 정하게 두지 않습니다. 상태 전이는 코드가 결정합니다. 이래야 재현 가능하고, 검색 예산을 통제할 수 있고, 판정 게이트를 강제할 수 있습니다.

---

## 1. 전체 파이프라인

```
[입력 1회: IMAGE / URL / TEXT — 프롬프트 없음]
  │
  ├─ S0. INTAKE                                    [검색 0]
  │    IMAGE → Vision OCR / URL → 본문 추출 / TEXT → 통과
  │    출력: {브랜드, 제품, 원문 문구[], 맥락}
  │    ▸ 왜 먼저: 반례 검색에는 '범주어'가 필수. 범주 없이는 쿼리를 만들 수 없음
  │
  ├─ S1. CLAIM TRIAGE                              [검색 0]
  │    각 문구 → FALSIFIABLE / PUFFERY / NOT_A_CLAIM
  │    FALSIFIABLE은 claim_type으로 세분류 (고정 vocabulary, PRD N5)
  │    ▸ 왜 여기서 검색을 안 하는가: puffery에 검색을 태우면 비용 낭비이자
  │      '그럴듯한 쓰레기' 생성. 조기 종료 게이트이며 Prompt Quality 시연 지점
  │    ▸ PUFFERY로 판정되면 여기서 종료. tool_call 0건 (PRD N4)
  │
  ├─ S2. 병렬 분기 ────────────────┬──────────────────────┐
  │                                 │                      │
  │  S2a. VERIFICATION ROUTER       │  S2b. INDUSTRY CLASSIFIER
  │   claim → SCIENTIFIC / GENERAL  │   임베딩 → 벡터 유사도 → 카테고리 배정
  │   ▸ 왜 분리: 학술 근거를 요구하는 │   임계 미달 시 신규 카테고리 생성
  │     주장과 일반 사실관계 주장은  │   ▸ 왜 병렬: 판정 로직에 영향을 주지 않음.
  │     깨는 방법 자체가 다름        │     실패해도 검증은 정상 작동해야 함
  │                                 │   ▸ 왜 필요: canonical 매칭의 파티션 키
  │                                 │
  ├─ S3. CACHE ROUTING (결정론적, LLM 아님)         [검색 0]
  │    같은 industry_category 파티션 내에서만 canonical 매칭
  │      ├ 매칭 실패                        → S4 (풀 검색)
  │      ├ 매칭 + needs_reverification=true → S4 (풀 검색)
  │      ├ 매칭 + TTL 이내                  → 캐시 즉시 반환, S4~S6 스킵
  │      └ 매칭 + TTL 초과 + 이의 없음      → S4 (델타 모드: date_from 지정)
  │    ▸ 왜 LLM이 아닌가: 재현 가능해야 하고, 캐시 판단은 판단이 아니라 규칙
  │    ▸ 왜 S2 뒤: 카테고리가 확정돼야 매칭 파티션이 정해짐
  │
  ├─ S4. REFUTATION HYPOTHESIS                     [검색 0]
  │    "이 주장을 깨려면 무엇이 존재해야 하는가"를 가설화
  │      순위주장 → ① 선행 사례 ② 다른 1위 주장자 ③ 인용된 조사기관 원본
  │      인증주장 → ① 인증 DB 실재 여부 ② 인증 범위와 광고 범위 일치 여부
  │      성능주장 → ① 측정 조건 명시 여부 ② 독립 측정 결과
  │    가설당 검색 쿼리 2~3개 생성 (검색 예산 상한 준수)
  │    ▸ 이 단계가 Pipeline Architecture 25%의 심장.
  │      2번 화면에 에이전트의 추론이 쿼리 형태로 그대로 읽힘
  │
  ├─ S5. COUNTER-EVIDENCE SEARCH (LINER, 병렬)     [검색 다수]
  │    route == SCIENTIFIC → liner_scholar_search
  │    route == GENERAL    → liner_web_search
  │    각 결과를 falsifier_spec 기준으로 평가 → counterexample_candidate 생성
  │      applicability_check = {scope_match, metric_match, timeframe_match, target_match}
  │    ▸ 조기 종료: 필수 필드를 전부 충족하는 candidate 1건 확정 시 잔여 탐색 중단
  │      (단순 문자열 일치만으로는 조기 종료하지 않음 — 오판정 방지)
  │
  └─ S6. VERDICT ASSEMBLY (결정론적 + 2단 가드레일)
       ① REFUTED 게이트: required_match_fields 전부 true → REFUTED, 아니면 NOT_REFUTED
          (PRD N1 — LLM 선언이 아니라 코드 조건문)
       ② 가드레일 1단: LLM output guardrail로 법적 결론 어휘 1차 차단
       ③ 가드레일 2단: 최종 JSON에 정규식 금지어 검사 → 걸리면 재생성 1회
          (SDK 가드레일은 중간 출력에 자동 적용되지 않으므로 코드 검사 필수)
       ④ DB 기록 + 스트림 push
       │
       └─ (응답 반환 이후, 비동기) FEEDBACK
            👍/👎 수집 → dispute 임계 초과 시 needs_reverification=true
            ▸ 응답을 절대 블로킹하지 않음 (PRD N2)
```

---

## 2. 상태 머신

애플리케이션이 소유합니다. LLM은 `RESEARCHING` 안에서만 승인된 툴을 선택·파라미터화할 수 있습니다.

```
[*] → INTAKE
INTAKE → TRIAGE
TRIAGE → COMPLETE          (전부 PUFFERY/NOT_A_CLAIM인 경우, 검색 0회)
TRIAGE → CLASSIFYING
CLASSIFYING → CACHE_CHECK
CACHE_CHECK → SYNTHESIZING (캐시 히트)
CACHE_CHECK → RESEARCHING  (미스 / 델타 / 재검증)
RESEARCHING → EVALUATING   (예산 소진 또는 조기 종료)
EVALUATING → SYNTHESIZING
SYNTHESIZING → PERSISTING → COMPLETE
RESEARCHING → DEGRADED     (프로바이더 장애 또는 JOB_TIMEOUT_SECONDS 초과)
EVALUATING → DEGRADED      (JOB_TIMEOUT_SECONDS 초과 — 그 시점까지 평가된 candidate만 반영)
DEGRADED → SYNTHESIZING    (부분 증거로 판정, 사유 명시)
INTAKE → FAILED
```

**DEGRADED가 중요한 이유**: 라이브 데모 중 LINER가 타임아웃되면 무한 스피너가 도는 게 최악입니다. 반드시 결정론적으로 종료되어야 하고, 그 경우 `PUBLIC_SUBSTANTIATION_NOT_FOUND` + 사유를 냅니다.

**JOB_TIMEOUT_SECONDS도 같은 이유로 DEGRADED를 씁니다** (`DECISIONS.md` D-13). 새로운 상태를 추가하지 않고 기존 프로바이더-장애 경로를 재사용하는 이유는, 사용자/심사위원 입장에서 "LINER가 느려서 못 끝냄"과 "시간 예산을 다 써서 그만둠"이 결과적으로 동일한 처리(부분 증거로 결정론적 종료)여야 하기 때문입니다.

---

## 3. 검색 예산 (필수 — 무제한 검색 금지)

claim 1건당 상한:
- SCIENTIFIC 경로: Scholar 쿼리 최대 3개
- GENERAL 경로: Web 쿼리 최대 4개
- 델타 모드: 위의 절반 (이미 과거 증거가 있으므로)
- 전체 상한 초과 시 즉시 EVALUATING으로 전이

예산 상한은 `claim_type.default_search_budget`에서 읽습니다. 하드코딩하지 마세요.

**왜 예산이 필요한가**: 무제한 검색은 "에이전트가 계획 없이 헤맨다"는 인상을 주고, 시간과 무관하게 그 자체로 비용·품질 문제입니다. 쿼리 개수를 통제하는 이 예산은 **탐색 범위**에 대한 안전장치이고, 아래 §3.1의 시간 예산과는 별개입니다.

### 3.1 전역 시간 예산 (JOB_TIMEOUT_SECONDS)

**목표 응답시간은 클레임 1건당 3~5분 소프트 실링입니다** (`DECISIONS.md` D-13 — 초기 1~2분 목표에서 완화됨). "소프트"라는 건 타이머로 응답을 강제로 끊는 게 목적이 아니라, LINER나 모델 호출이 예상보다 오래 걸려도 **무한정 대기하지는 않는다**는 하한선이라는 뜻입니다.

```
JOB_TIMEOUT_SECONDS (환경변수, 기본값 예: 270초 = 4.5분, 3~5분 범위 내 설정값)
```

- 체크 시점: RESEARCHING(LINER 검색 실행 중) 및 EVALUATING(S5 candidate 평가 중) 단계에서 누적 경과시간을 확인
- 초과 시: 진행 중이던 개별 호출은 완료를 기다리되, **새로운 검색/평가를 추가로 시작하지 않고** 그 시점까지 확보된 candidate만으로 DEGRADED → SYNTHESIZING으로 강제 전이 (§2)
- 상태머신을 새로 만들지 않고 기존 `DEGRADED` 경로를 그대로 씁니다 — 프로바이더 장애든 시간 예산 소진이든, 사용자에게는 "부분 증거로 결정론적으로 끝났다"는 동일한 경험이어야 하기 때문입니다
- 다른 임계값들과 마찬가지로 **미검증 추정치**입니다. `BUILD_PLAN.md` M6에서 실측 후 조정하세요

**§5(증거 적용가능성 평가) 폭도 별도로 제한합니다**: 시간 예산과 별개로, `NOT_REFUTED`로 끝나는 경로(조기 종료 없음)에서는 검색 결과 전량이 `gpt-5.6-sol`(high effort)로 평가됩니다. 이건 시간 여유가 있어도 비용이 무제한으로 커지는 지점이라, `claim_type.max_evidence_per_query`로 쿼리당 평가 대상 문서 수를 상한 걸어둡니다 (`DB_SCHEMA.md` 참조).

---

## 4. 라우팅 규칙 (S2a)

| route | 트리거 | 도구 |
|---|---|---|
| `SCIENTIFIC` | "과학적으로 입증된", "임상적으로 검증된", "연구 결과에 따르면", "논문에서", 성분·효능·의학적 효과 주장 | LINER Scholar |
| `GENERAL` | 그 외 전부 — "국내 최초", "업계 1위", "유일한", 수상·인증·점유율 주장 | LINER Web |

**안전장치 (P0)**: `claim_type`이 `CLINICAL_COMPLETION`인 경우 라우터 판단과 무관하게 **항상 SCIENTIFIC으로 강제**합니다. 임상 주장이 Web 경로로 새면 검증이 무의미해집니다.

**경계가 애매한 경우** (예: "전문가들이 인정한"): 기본값 `GENERAL`. 시간이 남으면 Scholar에서 관련 문헌이 실제로 잡히면 SCIENTIFIC으로 재시도하는 2단계 폴백을 추가하되, P2입니다.

---

## 5. 업종 분류 (S2b)

```python
def resolve_industry_category(text) -> (category_id, similarity, is_new):
    emb = embed(text)
    top = vector_search(emb, industry_category.centroid_embedding, k=5)
    if top and cosine(emb, top[0].centroid) >= CATEGORY_REUSE_THRESHOLD:
        return top[0].id, score, False          # 기존 재사용 (우선)
    new = create_category(                       # 신규 생성
        code=llm_generate_slug(text),
        label=llm_generate_label(text),
        centroid_embedding=emb,
        created_by='agent_generated'
    )
    return new.id, None, True
```

- `CATEGORY_REUSE_THRESHOLD` 초기값 **0.75** — 미검증 추정치입니다 (PRD §10-5)
- **기존 카테고리 재사용을 우선**해야 합니다. 안 그러면 "화장품"/"뷰티"/"코스메틱"이 각각 생겨서 파티셔닝의 목적(캐시 히트 집중)이 무너집니다
- 분류 실패 시에도 검증 파이프라인은 정상 작동해야 합니다. 카테고리는 매칭 파티션 키일 뿐, 판정 로직에 관여하지 않습니다
- 동시 요청으로 유사 카테고리가 중복 생성될 수 있습니다. 라벨 해시 기준 single-flight 락을 권장하지만 P2입니다 (최악의 결과가 "그 카테고리 캐시 히트율이 일시적으로 낮아짐"이지 오판정이 아님)

---

## 6. 이벤트 스트림

모든 단계에서 `trace_event` 테이블에 이벤트를 INSERT합니다 (`DB_SCHEMA.md`). 별도 SSE 서버는 두지 않습니다 — Streamlit 세컨드 화면 페이지가 이 테이블을 폴링해서 구독합니다 (`BUILD_PLAN.md` §1.2, `DECISIONS.md` D-14).

```
job.created
intake.completed
claim.extracted
claim.triaged            (PUFFERY면 여기서 job.completed로 직행)
route.decided            (SCIENTIFIC / GENERAL)
industry.classified      (is_new=true면 UI에서 강조)
cache.decision            (HIT / MISS / DELTA / REVERIFY)
tool.call                ← raw, 가공 금지
tool.result              ← raw, 가공 금지
candidate.evaluated      (applicability_check 포함)
verdict.assembled
job.completed | job.failed | job.degraded
```

`tool.call` / `tool.result`는 **가공 없이** 기록합니다 (대회 필수 요건). API 키·인증 헤더만 마스킹하고 나머지는 그대로. LINER 호출과 OpenAI 호출을 구분할 수 있도록 `provider` 컬럼을 넣으세요 — 세컨드 화면에서 색을 다르게 표시해 "둘 다 실제로 쓰고 있다"를 시각적으로 증명합니다.

LINER Search는 스트리밍 응답이 아니므로, 파이프라인 코드가 요청 전후로 자체 `tool.call`/`tool.result` row를 감싸서 INSERT합니다.

---

## 7. 예외 처리

| 상황 | 처리 |
|---|---|
| Vision OCR 실패 | 실패 로그 남기고 가능한 부분만 처리. 전부 실패 시 텍스트 입력 안내 |
| LINER 타임아웃/429 | 재시도 1회 (백오프) → 실패 시 DEGRADED → `PUBLIC_SUBSTANTIATION_NOT_FOUND` + 사유 |
| OpenAI structured output 스키마 위반 | fail-closed, 재시도 1회. 2회 실패 시 job.failed |
| 검색 결과 0건 | `NOT_REFUTED` (정상 경로. 오류 아님) |
| 발행일(date) 없는 문서 | timeframe_match = false 처리. **날짜를 추측하지 말 것** |
| 카테고리 분류 실패 | 기본 카테고리로 폴백하고 검증은 계속 진행 |
| `JOB_TIMEOUT_SECONDS` 초과 (RESEARCHING/EVALUATING 중) | 진행 중이던 호출만 마무리, 신규 호출 중단 → DEGRADED → 확보된 candidate로 판정 (§3.1, D-13) |
