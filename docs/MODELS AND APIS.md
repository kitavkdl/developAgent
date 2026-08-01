# COUNTER — 모델 고용 명세 & API 연동

> **모델 정보 확인 시점: 2026-08-01, OpenAI 공식 문서(developers.openai.com) 기준.**
> LINER 쪽 파라미터명은 **미확인 항목이 있습니다.** §3의 표시를 반드시 확인하세요.

---

## 1. 전체 구성

| 제공자 | 역할 | 개수 |
|---|---|---|
| **LINER** | 검색 실행 전담 | 2개 (Web / Scholar) |
| **OpenAI** | 그 외 전부 (이해·판단·분류·조립) | 3개 텍스트 모델 + 1개 임베딩 모델 |

**OpenAI 내장 web_search 툴은 쓰지 않습니다.** 검색은 전부 LINER를 통합니다. (`DECISIONS.md` D-04)

---

## 2. OpenAI 모델 배정

### 2.1 사용 가능한 모델 (2026-08-01 공식 카탈로그 확인)

| Model ID | 성격 | Input | Output | 컨텍스트 | 지식컷오프 |
|---|---|---:|---:|---:|---|
| `gpt-5.6-sol` (별칭 `gpt-5.6`) | 플래그십, 복잡한 추론 | $5/MTok | $30/MTok | 1.05M | 2026-02-16 |
| `gpt-5.6-terra` | 지능/비용 균형 | $2/MTok | $12/MTok | 1.05M | 2026-02-16 |
| `gpt-5.6-luna` | 저비용 대량 처리 | $0.20/MTok | $1.20/MTok | 1.05M | 2026-02-16 |
| `text-embedding-3-small` | 임베딩, 1536차원 | 저가 | — | 8192 입력 | — |

모든 gpt-5.6 계열은 텍스트+이미지 입력, 멀티링구얼, 비전을 지원하고 `reasoning.effort`를 `none / low / medium / high / xhigh / max`로 조절할 수 있습니다. Responses API로 호출합니다.

### 2.2 단계별 배정 (근거 포함)

| 단계 | 모델 | reasoning.effort | 왜 이 모델인가 |
|---|---|---|---|
| **S0 INTAKE (Vision OCR)** | `gpt-5.6-terra` | `low` | 이미지→텍스트는 추론보다 인식 작업. 플래그십을 쓸 이유가 없고, luna는 저해상도 한국어 캡처에서 위험. 실측(PRD §10-3) 결과 품질 부족하면 `sol`로 승급 |
| **S1 CLAIM TRIAGE** | `gpt-5.6-terra` | `medium` | 제품의 핵심 판단부. PUFFERY/FALSIFIABLE 경계와 claim_type 분류가 여기서 결정되므로 저가 모델은 부적절. 다만 정형화된 분류라 sol까지는 불필요 |
| **S2a ROUTER** | `gpt-5.6-luna` | `low` | SCIENTIFIC/GENERAL 이진 분류. 단순 작업이므로 최저가. **단 CLINICAL_COMPLETION 강제 규칙이 코드에 있으므로** 오분류 리스크가 코드로 완화됨 |
| **S2b 카테고리 라벨 생성** | `gpt-5.6-luna` | `low` | 신규 카테고리의 slug/label 생성. 짧은 문자열 생성 |
| **S4 REFUTATION HYPOTHESIS** | `gpt-5.6-sol` | `high` | **여기가 플래그십을 쓸 유일한 이유입니다.** "이 주장을 깨려면 무엇이 존재해야 하는가"는 창의적 역발상이 필요하고, 이 단계 품질이 곧 Pipeline Architecture 25% 점수 |
| **S5 증거 적용가능성 평가** | `gpt-5.6-sol` | `high` | scope/metric/timeframe/target 각각의 일치 여부를 판단. 오판정이 여기서 시작되므로 최고 성능 필요. 출력은 boolean 4개(structured output)이며 **최종 판정은 코드가 조립**. 평가 대상 수는 `claim_type.max_evidence_per_query`로 상한 (`DB_SCHEMA.md`, `DECISIONS.md` D-13) |
| **S6 가드레일 1단** | `gpt-5.6-luna` | `none` | 금지 어휘 검사. 2단(정규식)이 뒤에 있으므로 여기는 가벼워도 됨 |
| **임베딩 (카테고리 + canonical)** | `text-embedding-3-small` | — | 1536차원. `-large`(3072)는 지연·비용 대비 이득이 작음. **카테고리 임베딩과 claim 임베딩은 반드시 같은 모델**을 쓸 것 (섞으면 유사도가 무의미) |

### 2.3 비용 감각

해커톤 크레딧 한도가 있습니다. 위 배정에서 `sol`은 S4/S5에만 들어가고 나머지는 terra/luna입니다. 데모 리허설을 반복하면 비용이 누적되므로, **캐시가 실제로 작동하면 리허설 비용도 같이 내려갑니다** — 캐시를 일찍 만들 실용적 이유이기도 합니다.

### 2.4 공통 호출 규칙

- **Structured Outputs를 모든 분류/평가 단계에 강제**합니다. 자유 텍스트 파싱 금지.
- Structured Outputs는 **구조만 보장하고 내용의 사실성은 보장하지 않습니다.** 그래서 판정은 별도 코드 게이트를 통과해야 합니다 (PRD N1).
- 스키마 위반 시 fail-closed + 재시도 1회.
- 모델 ID는 전부 환경변수/설정으로 뺍니다. 하드코딩 금지 (모델 승급/강등을 즉시 하기 위해).

```
OPENAI_MODEL_INTAKE=gpt-5.6-terra
OPENAI_MODEL_TRIAGE=gpt-5.6-terra
OPENAI_MODEL_ROUTER=gpt-5.6-luna
OPENAI_MODEL_HYPOTHESIS=gpt-5.6-sol
OPENAI_MODEL_EVALUATOR=gpt-5.6-sol
OPENAI_MODEL_GUARDRAIL=gpt-5.6-luna
OPENAI_MODEL_EMBEDDING=text-embedding-3-small
```

### 2.5 시크릿·설정값 관리 (Streamlit 배포, `DECISIONS.md` D-14 이후 추가)

리포가 public이므로 위 env var 목록과 API 키·DB 연결 문자열은 **같은 방식으로 관리하되 다른 파일에 둡니다**:

- 로컬 개발: `.streamlit/secrets.toml` (git-ignored). `.streamlit/secrets.toml.example`을 템플릿으로 복사해서 씁니다.
- 배포: Streamlit Cloud 앱 설정의 **Secrets**에 동일한 키를 등록합니다. 리포에는 절대 올라가지 않습니다.
- 코드에서는 `st.secrets["OPENAI_MODEL_HYPOTHESIS"]`처럼 읽습니다.

**⚠️ 확인 필요 (미검증)**: Streamlit이 `secrets.toml`의 값을 `os.environ`에도 자동으로 반영하는지는 버전에 따라 달라질 수 있어 이 문서에서 단정하지 않습니다. `os.getenv(...)` 기반으로 이미 짜둔 코드가 있다면, 앱 시작 시점에 아래처럼 명시적으로 브리지하는 편이 안전합니다.

```python
import os, streamlit as st
for k, v in st.secrets.items():
    os.environ.setdefault(k, str(v))
```

이렇게 하면 `MODELS_AND_APIS.md` §2.4의 env var 목록과 `DB_SCHEMA.md`/`ARCHITECTURE.md`가 가정하는 `os.environ` 기반 설정 읽기 방식을 코드 변경 없이 그대로 유지할 수 있습니다.

---

## 3. LINER 연동 — 2개 검색 모델

### 3.1 고용하는 2개

| 이름 | 용도 | 호출 조건 |
|---|---|---|
| **LINER Web Search** | 일반 사실관계 반례 (최초/1위/유일/점유율/수상) | `route == GENERAL` |
| **LINER Scholar Search** | 학술·임상 근거 반례 | `route == SCIENTIFIC` |

두 모드 모두 **제목 / URL / 스니펫(설명) / 날짜 메타데이터**를 구조화 JSON으로 반환합니다. 우리에게 필요한 건 합성된 답변이 아니라 **URL과 발행일이 붙은 '문서의 존재'**이므로 Search API를 씁니다.

### 3.2 ⚠️ 착수 전 반드시 확인할 것 (아직 미확인)

아래는 **문서에서 확정 확인하지 못한 항목**입니다. 코드에 하드코딩하기 전에 실제 호출로 검증하세요.

| # | 확인 항목 | 확인 방법 | 실패 시 |
|---|---|---|---|
| L1 | Web / Scholar 각각의 정확한 엔드포인트 URL과 요청 파라미터명 | 공식 문서 + 실제 호출 1회 | 진행 불가, 즉시 팀에 보고 |
| L2 | 응답 필드명 (title/url/description/date/citation_count 등)과 `date` 필드의 실제 커버리지 | 한국어 결과 30건 표본 | 커버리지 낮으면 timeframe 요구 완화 |
| L3 | **날짜범위 필터 파라미터 지원 여부** (`published_after` 등) | 문서 + 실제 호출 | **미지원 시 델타 서치 전체 스코프 아웃** (PRD §10-4) |
| L4 | 최대 결과 수 상한 및 페이지네이션 지원 여부 | 문서 | 상한이 낮으면 가설을 잘게 쪼개서 우회 |
| L5 | Rate limit (기본값 및 429 동작) | 문서 | 리미터 값 조정 |

**참고**: Scholar Search의 기본 QPS 제한이 낮을 수 있습니다(문서상 2 QPS로 알려짐, 재확인 필요). 병렬 호출 시 리미터를 반드시 넣고, 429를 처리하고, 프로바이더 request ID를 트레이스에 남기세요.

### 3.3 클라이언트 구현 요구사항

```python
class LinerClient:
    # 필수
    - timeout 설정 (권장 15s)
    - QPS 리미터 (실측한 값 기준, 안전하게 그 절반)
    - 429 → 지수 백오프 재시도 1회
    - 모든 호출에 대해 tool.call / tool.result 이벤트 발행 (provider="liner")
    - request_id를 search_log에 기록
    - API 키는 서버 사이드 환경변수(§2.5). 로그/트레이스에 절대 노출 금지
```

### 3.4 쓰지 않는 LINER API

Search Agent / Deep Research / Quick Answer / Visualization은 **이번 스코프에 없습니다.**

이유 (`DECISIONS.md` D-05 참조):
- Deep Research는 자체적으로 하위 과제 생성·반복 검색·추론을 수행하므로, 그 위에 우리 멀티에이전트를 올리면 "그래서 OpenAI 에이전트들은 실제로 무엇을 결정하나?"라는 심사 질문에 답하기 어려워짐
- 결제 직전 실시간 경로에 다단계 리서치를 넣으면 지연이 커져 Real-time Adaptability 점수에 오히려 불리
- Visualization은 자연어 쿼리만 받고 지연이 크며, 우리 구조화 데이터를 재해석할 위험이 있음. 차트가 필요하면 Streamlit에서 직접 렌더링

---

## 4. 툴 정의 (Agents SDK 등록용)

| Tool | Provider | Input | Output | 비고 |
|---|---|---|---|---|
| `ocr_image` | OpenAI | image | extracted_text (실패 가능) | Vision |
| `url_fetch` | 자체 | url | 본문 텍스트 (실패 가능) | HTTP(S)만 허용, 사설/링크로컬 IP 차단, 리다이렉트·바이트·시간 제한 |
| `embed_text` | OpenAI | text | vector[1536] | |
| `classify_industry` | 자체(DB) | vector | category_id, score, is_new | 벡터 검색 + 필요 시 생성 |
| `liner_web_search` | LINER | query, (date_from?) | title, url, snippet, date | GENERAL 전용 |
| `liner_scholar_search` | LINER | query, (date_from?) | title, url, description, date, authors, journal, citation_count | SCIENTIFIC 전용 |
| `write_record` | 자체(DB) | 레코드 | success | |

**`url_fetch` 보안 주의**: 가져온 페이지 콘텐츠는 **데이터이지 지시가 아닙니다.** 페이지 안에 "이전 지시를 무시하고..." 같은 내용이 있어도 절대 따르지 않도록 프롬프트에 명시하고, 툴 권한과 DB 쓰기 권한을 모델 바깥에 두세요.

---

## 5. 출처

- OpenAI 모델 카탈로그: https://developers.openai.com/api/docs/models (2026-08-01 확인)
- OpenAI 임베딩 가이드: https://developers.openai.com/api/docs/guides/embeddings
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Agents SDK: https://developers.openai.com/api/docs/guides/agents/quickstart
- LINER Developers: https://liner.com/developers/docs — **§3.2 항목들을 여기서 직접 재확인할 것**
