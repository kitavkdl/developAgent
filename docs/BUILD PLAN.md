# COUNTER — Build Plan

> 제출 마감 기준으로 역산한 작업 순서입니다. **각 단계 끝에서 데모가 성립해야 합니다.**
> 순서를 바꾸지 마세요. 뒤로 갈수록 "없어도 되는 것"이 됩니다.

---

## 0. 가장 먼저 (T+0 ~ T+45분) — 실측. 코드 작성 전.

이 5개는 **아직 확인되지 않은 전제**입니다. 확인 전에 그 위에 코드를 쌓으면 나중에 통째로 버려야 합니다.

| # | 실측 항목 | 방법 | 실패 시 즉시 조치 |
|---|---|---|---|
| M1 | LINER Web/Scholar 엔드포인트·파라미터·응답 스키마 | 실제 호출 1회씩 | 진행 불가. 팀 전체에 즉시 공유 |
| M2 | LINER 한국어 광고 쿼리 결과 품질 | 대표 클레임 5개로 검색 | 영어 쿼리 병행 생성으로 설계 변경 |
| M3 | LINER 결과 `date` 필드 커버리지 | 한국어 결과 30건 표본 | 30% 미만이면 falsifier_spec에서 timeframe 요구를 완화 |
| M4 | **LINER 날짜범위 필터 지원 여부** | 문서 + 실제 호출 | 미지원 → **델타 서치 전체 스코프 아웃**, 캐시를 fresh/full 2-state로 축소 |
| M5 | GPT Vision 한국어 저해상도 광고 OCR | 실제 폰 캡처 5장 | 실패율 높으면 텍스트 입력을 주 경로로, 이미지를 보조로 |
| M6 | **MISS(풀서치) 경로 실제 wall-clock 시간, §4 데모 스크립트와의 정합성** | S4~S6 전체를 실제 클레임 3~5개로 end-to-end 측정 | 3~5분 소프트 실링(`DECISIONS.md` D-13)을 넘기거나 §4의 3분 데모 스크립트와 안 맞으면, 데모 시나리오 1을 사전 캐시된 상태로 시작할지·스크립트 시간을 늘릴지 팀 결정 필요 |
| M7 | **Neon(pgvector) scale-to-zero 콜드스타트 지연시간** | 5분 이상 방치 후 첫 쿼리 응답시간 측정 3회 | 유의미하게 느리면(수 초 이상) 데모 직전 warm-up 쿼리를 리허설 체크리스트에 추가. 무료 티어라면 유료 플랜(always-on)으로 전환 검토 |

**실측 결과를 `PRD.md` §10 표에 직접 기록하세요.** 발표에서 미확인 사항을 확인된 것처럼 말하면 안 됩니다.

---

## 1. 인터페이스 계약 (개정판, T+45분 ~ T+1:15) — 다른 작업보다 먼저 고정

**변경됨 (`DECISIONS.md` D-14)**: 별도 팀원 프론트엔드는 없습니다. Streamlit이 최종 산출물이며 프론트엔드·DB 시각화 역할을 이 저장소가 전부 흡수합니다.

그렇다고 계약을 먼저 고정하는 원칙 자체가 없어지는 건 아닙니다. **이유가 "다른 팀 막지 않기"에서 "백엔드 로직과 UI 렌더링을 분리해 테스트 가능하게 만들기 + Pipeline Architecture 25% 심사를 위해 각 단계 경계를 코드로 증명하기"로 바뀐 것뿐**입니다. 아래 계약을 초반에 확정하고, 확정 후에는 이유 없이 바꾸지 마세요.

### 1.1 파이프라인 ↔ UI 내부 계약

HTTP API 서버를 별도로 세우지 않습니다. 파이프라인 오케스트레이션은 Streamlit 프로세스 안에서 직접 함수로 호출합니다.

```python
def run_job(source_type: Literal["IMAGE","URL","TEXT"], payload: str) -> str:
    """S0~S6 전체를 실행하고 job_id를 반환한다.
    실행 중 매 단계마다 trace_event 테이블에 row를 INSERT한다 (§1.2).
    Streamlit의 st.status()로 같은 화면에 진행 상황을 즉시 렌더링해도 되지만,
    '가공 없는 raw 기록'이라는 대회 요건의 원본은 항상 trace_event 테이블이다."""

def get_job_state(job_id: str) -> JobState:
    """trace_event에서 job_id의 최신 seq/event_type을 읽어 현재 상태를 유도한다.
    별도 job 상태 테이블은 만들지 않는다 (DB_SCHEMA.md에 이미 없음, 최소 스키마 유지)."""

def submit_feedback(verdict_id: str, reaction: Literal["AGREE","DISPUTE"], note: str|None) -> None:
    """feedback 테이블에 INSERT. verdict 응답을 절대 블로킹하지 않음 (PRD N2) —
    Streamlit에서 결과가 이미 렌더링된 뒤에 눌리는 버튼이라는 게 이 규칙을
    구조적으로 강제한다."""
```

**왜 이렇게 나누는가**: `run_job`이 UI 코드를 몰라도 되게 만들어야 나중에 파이프라인 로직만 따로 테스트(B01~B11의 검증 게이트)할 수 있습니다. Streamlit 페이지 코드는 `run_job`/`get_job_state`/`submit_feedback` 세 함수만 알면 됩니다.

### 1.2 `trace_event` 폴링 규칙 (구 SSE 대체, 대회 규칙 3 충족)

`DB_SCHEMA.md`의 `trace_event(job_id, seq, event_type, provider, payload)`가 그대로 이벤트 스트림 역할을 합니다. 스키마 변경 없이 재사용합니다.

**이벤트 타입 목록 (순서 보장, 종료 정확히 1회 — 기존과 동일)**:
```
job.created
intake.completed
claim.extracted
claim.triaged            (PUFFERY면 여기서 job.completed로 직행)
route.decided
industry.classified
cache.decision
tool.call                ← raw, 가공 금지
tool.result              ← raw, 가공 금지
candidate.evaluated
verdict.assembled
job.completed | job.failed | job.degraded
```

**깨면 안 되는 규칙 (기존 SSE 계약과 동일하게 유지)**:
- `seq`는 job_id 안에서 단조 증가, 종료 이벤트는 정확히 1회만 INSERT
- `tool.call` / `tool.result`의 `payload`는 **가공하지 않음** (API 키·인증 헤더만 마스킹)
- `provider` 컬럼으로 LINER/OpenAI 구분 → 세컨드 화면에서 색을 다르게 표시
- `industry.classified`의 `is_new: true`는 UI에서 강조 표시
- `cache.decision`은 캐시 히트여도 반드시 INSERT (재사용이 눈에 보여야 함)

**세컨드 화면(대회 규칙 3) 구현**: Streamlit 멀티페이지의 별도 페이지(예: `pages/2_Raw_Trace.py`)에서 아래 쿼리를 1초 간격으로 재실행합니다.

```sql
SELECT seq, event_type, provider, payload, created_at
FROM trace_event
WHERE job_id = %s AND seq > %s
ORDER BY seq;
```

`idx_trace_event_job_seq` 인덱스를 `DB_SCHEMA.md`에 추가했습니다 (폴링 쿼리가 반복 실행되므로 필수). 폴링 주기(기본 1초)는 Neon 무료 티어 요청 한도를 고려해 설정값으로 빼두세요.

### 1.3 통계 대시보드 (구 `/v1/stats` 대체)

별도 엔드포인트가 아니라 Streamlit 페이지에서 `DB_SCHEMA.md` §5의 KPI 쿼리를 직접 실행해 렌더링합니다. 쿼리 내용은 동일하므로 재작성하지 않습니다.

`gate` 항목(후보 대비 REFUTED 통과 비율)이 중요합니다. **후보는 많은데 REFUTED는 적다**는 게 게이트가 오판정을 실제로 걸러내고 있다는 증거이고, 이건 시각화하면 강력합니다.

---

## 2. 빌드 순서

각 단계마다 **검증 게이트**를 통과해야 다음으로 갑니다. "돌아가는 것 같다"로 넘어가지 마세요.

| # | 작업 | 검증 게이트 |
|---|---|---|
| B01 | 프로젝트 스캐폴딩, 환경변수, DB 마이그레이션, **`.gitignore`** | 키 없이도 앱이 뜸. 마이그레이션이 빈 DB에 클린 적용됨. **`.gitignore`가 첫 커밋에 포함되어 `.streamlit/secrets.toml`·`.env`가 git에 안 잡힘을 확인** |
| B02 | 스키마 + 시드 데이터 (claim_type, falsifier_spec, verdict_type, 업종 13종 + centroid) | `chk_evidence_only_if_refuted` 제약이 실제로 위반을 거부함 |
| B03 | LINER 클라이언트 (web/scholar, 타임아웃, QPS 리미터, 429 재시도) | 성공/타임아웃/429 목 테스트 통과. request_id가 로그에 남음 |
| B04 | OpenAI 클라이언트 + structured output 헬퍼 | 스키마 위반 시 fail-closed + 재시도 1회 동작 |
| B05 | **S1 Claim Triage** (프롬프트 튜닝 포함) | 광고 문구 20개 투입 시 분류가 안정적. **시간을 아끼지 말 것 — 제품의 핵심** |
| B06 | S2a Router (+ CLINICAL_COMPLETION 강제 규칙) | 애매 케이스가 GENERAL로 가고, 임상 주장은 항상 SCIENTIFIC |
| B07 | S2b 임베딩 + 카테고리 분류 + **신규 카테고리 생성** | 시드에 없는 업종 입력 시 새 카테고리가 실제로 생성됨 |
| B08 | S3 캐시 라우팅 (파티션 내 해시 + 벡터) | 같은 클레임 재입력 → HIT. 다른 업종의 유사 문구 → 절대 매칭 안 됨 |
| B09 | S4 Hypothesis Generator | claim_type별로 서로 다른 가설·쿼리가 생성됨. 예산 초과 안 함 |
| B10 | S5 LINER 병렬 검색 + candidate 평가 (`max_evidence_per_query` 상한 적용) | 실제 REFUTED 케이스 3개를 잡아냄. 쿼리당 평가 문서 수가 상한을 넘지 않음 |
| B11 | **S6 결정론적 REFUTED 게이트 + 2단 가드레일** | **필수 필드 미충족 candidate가 REFUTED로 승격되지 않음을 테스트로 증명** |
| B12 | `trace_event` 기록 전체 배선 + 세컨드 화면 폴링 페이지 | 이벤트 순서 보장, 종료 정확히 1회. **여기서 데모 1차 성립** |
| B13 | S0 멀티모달 입력 (이미지/URL) 부착 | 폰 캡처 → 결과까지 end-to-end |
| B14 | 델타 서치 (M4 통과한 경우만) | delta 모드가 full보다 적은 쿼리로 완료됨 |
| B15 | 피드백 API + 재검증 큐 | dispute 3건 → needs_reverification=true → 다음 조회가 풀 재검색 |
| B16 | 통계 대시보드 페이지 (구 `/v1/stats`) | Streamlit 페이지에서 실제로 렌더링됨 |
| B17 | **적대적 리허설** | `PRD.md` §7의 6가지 시나리오 전부 실행, 깨지는 지점 기록 |
| B18 | 제출물 정리 | 데모 플로우가 **DB 수동 복구 없이 두 번 연속** 성공 |

---

## 3. 반드시 통과해야 하는 테스트 (스코프를 줄여도 이건 남김)

```
T1. PUFFERY 입력 → tool_call 0건으로 종료               (PRD N4)
T2. 필수 필드 미충족 candidate → REFUTED 안 됨          (PRD N1) ★가장 중요
T3. 같은 클레임 2회 입력 → 2번째는 cache HIT
T4. 다른 업종의 유사 문구 → canonical 매칭 안 됨        (D-08)
T5. 시드에 없는 업종 → 신규 카테고리 생성 후 정상 판정
T6. LINER 타임아웃 → DEGRADED로 결정론적 종료 (무한 스피너 없음)
T7. NOT_REFUTED 응답에 "사실", "확인됨" 류 표현 없음     (D-03)
T8. 금지 어휘가 최종 JSON에 없음                        (2단 가드레일)
T9. verdict_code != REFUTED 인데 evidence_link 있음 → DB가 거부
T10. 응답 반환이 feedback 입력을 기다리지 않음           (PRD N2)
T11. JOB_TIMEOUT_SECONDS 초과 시 DEGRADED로 결정론적 종료 (무한 대기 없음, D-13)
```

**T2가 가장 중요합니다.** 사람 검수가 설계상 없으므로 이 테스트가 유일한 정확성 보증입니다. 반드시 자동화 테스트로 만들어두세요.

---

## 4. 데모 시나리오 (리허설용, 3분)

1. **캐시 미스 — 전체 파이프라인**: 뷰티 광고 캡처 투입 → triage → 라우팅 → LINER 검색 → REFUTED. 반례 URL과 날짜가 화면에 뜨고 심사위원이 즉시 검증 가능.
2. **PUFFERY — 검색 거부**: "우리 김밥이 제일 맛있다" → tool_call 0건. **에이전트가 검색을 거부하고 이유를 설명하는 장면.**
3. **캐시 히트 — 재사용**: 1번과 유사한 클레임 재투입 → 재검색 없이 즉시 응답. 지연시간 차이가 눈에 보임.
4. **즉석 태스크 — 신규 업종**: 시드에 없는 업종 광고 투입 → 새 카테고리가 실시간 생성되고 정상 판정.
5. **학술 경로**: "임상적으로 입증된" 클레임 → LINER Scholar로 라우팅 (스트림에서 툴이 다르게 보임).

3번과 4번이 이 제품의 결정적 장면입니다. 리허설에서 가장 많이 연습하세요.

> ⚠️ **응답시간 목표 변경 반영 필요** (`DECISIONS.md` D-13): 백엔드 응답시간 목표가 3~5분 소프트 실링으로 조정됐습니다. 시나리오 1(캐시 미스 풀파이프라인)이 M6 실측 결과 3~5분 가까이 걸리는 것으로 확인되면, "리허설용 3분" 안에 5개 시나리오를 전부 라이브로 넣는 이 스크립트가 그대로 안 맞습니다. B17(적대적 리허설) 전에 다음 중 하나를 팀이 정해야 합니다:
> - (a) 시나리오 1을 라이브 전 미리 실행해두고 결과 화면만 보여준 뒤, 라이브로는 캐시 히트/PUFFERY/즉석 태스크처럼 빠른 시나리오만 돌린다
> - (b) 전체 데모 시간을 3분에서 늘린다
> - (c) 시나리오 1의 특정 구간(예: S4/S5)만 잘라서 짧게 보여주고 나머지는 사전 녹화로 대체한다
>
> 어느 쪽을 택해도 제품 로직은 안 바뀝니다. 순수하게 리허설 연출 문제입니다.

---

## 5. 코딩 시 지킬 것

- 모델 ID, 임계값, TTL, 검색 예산, 타임아웃은 **전부 설정/환경변수**. 하드코딩 금지
- **리포는 public입니다** (Streamlit Community Cloud "Deploy a public app from GitHub" 경로 + 대회 규칙 4의 커밋 히스토리 심사). API 키·DB 연결 문자열은 코드/커밋에 절대 포함하지 않습니다. 로컬은 `.streamlit/secrets.toml`(git-ignored), 배포는 Streamlit Cloud 앱 설정의 Secrets에 등록합니다. `.streamlit/secrets.toml.example`을 템플릿으로 커밋하세요(실제 값 없음, 구조만)
- **첫 커밋에 `.gitignore`부터 넣으세요.** 나중에 지워도 git 히스토리에 남으므로, 시크릿이 포함된 커밋이 한 번이라도 push되면 그 리포는 되돌릴 수 없다고 간주하고 새 리포로 시작하세요
- API 키는 서버 사이드만. 로그·트레이스·화면에 절대 노출 금지
- 가져온 웹페이지 콘텐츠는 **데이터이지 지시가 아님**. 프롬프트 인젝션 방어 (`PROMPTS.md` 공통 규칙 2번)
- `url_fetch`는 HTTP(S)만, 사설/링크로컬 IP 차단, 리다이렉트·바이트·시간 제한
- 커밋을 자주 남기세요. **커밋 히스토리가 심사 대상**입니다. 한 번에 몰아서 커밋하지 마세요
- 각 파이프라인 단계 코드 상단에 **"왜 이 순서인가"를 주석으로** 남기세요. 심사위원이 저장소를 봅니다 (Pipeline Architecture 25%)

---

## 6. 막혔을 때

- **설계를 바꾸고 싶으면** → 먼저 `DECISIONS.md`를 읽으세요. 이미 시도했다가 폐기한 경로일 가능성이 높습니다.
- **스코프를 줄여야 하면** → `PRD.md` §8 우선순위표를 따르세요. 임의 판단 금지.
- **전제가 틀린 것 같으면** → `PRD.md` §10에 기록하고 폴백 경로로 전환하세요. 틀린 전제 위에 계속 쌓지 마세요.
