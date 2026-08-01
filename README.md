# COUNTER

> 광고에서 **"국내 최초 / 업계 1위 / 임상 완료"** 같은 문구를 보고 결제 직전인 소비자를 위해,
> **그 주장을 깨는 반례가 공개 웹/학술 문헌에 실재하는지**를 자율적으로 찾아 보고하는 에이전트.
>
> AGENT:24 해커톤 (YAI × OpenAI) · LINER API Agent 트랙 제출물.

## 판정 계약 — 3단계 판정 + PUFFERY

| verdict | 의미 |
|---|---|
| `CONTRADICTED` | falsifier 기준(범주·지표·시점·주체)을 **전부** 충족하는 반박 근거 문서가 실재. 근거 URL 필수 |
| `CORROBORATED` | 위와 동일한 기준을 전부 충족하는 **뒷받침** 근거 문서가 실재. 근거 URL 필수하되 **"완전히 입증됐다"는 뜻은 아님** |
| `UNVERIFIED` | 실행한 N개 쿼리에서 반증도 뒷받침 근거도 미발견. **"사실이다"도 "거짓이다"도 아님** — 판단 유보. 실행 쿼리 전문과 탐색 범위(쿼리 수·검토 문서 수)를 그대로 노출 |
| `PUFFERY` | 주관적 과장. 검증 대상이 아니므로 **검색 tool_call 0건** |

신뢰도 점수(%)와 참/거짓 판정은 **의도적으로 만들지 않습니다**. 측정할 수 없는 것을 측정한 척하지 않습니다.
특히 `UNVERIFIED`는 "반례를 못 찾았으니 사실일 가능성이 높다" 식의 긍정 결론을 절대
내리지 않도록 프롬프트 지시 + 정규식 가드레일 이중으로 차단합니다 (`counter/guardrail.py`).

## 아키텍처 한 줄 요약

**LINER는 검색을 실행하고, OpenAI는 그 검색을 계획·평가·판정한다.**
오케스트레이션(상태 전이·검색 예산·3단계 게이트)은 전부 애플리케이션 코드가 소유하며,
LLM은 각 단계 안에서만 판단한다.

```
입력 1회 (IMAGE/URL/TEXT, 프롬프트 없음)
 → S0 INTAKE (Vision OCR / 본문 추출)          [검색 0]
 → S1 CLAIM TRIAGE (PUFFERY 조기 종료 게이트)   [검색 0]
 → S2a ROUTER (SCIENTIFIC/GENERAL) ∥ S2b 업종 분류 (신규 카테고리 즉석 생성)
 → S3 CACHE ROUTING (결정론적 — HIT/MISS/DELTA/REVERIFY)
 → S4 REFUTATION HYPOTHESIS ("깨려면 무엇이 존재해야 하는가")
 → S5 LINER 검색 (Web/Scholar) + 증거 적용가능성 평가 (반박/뒷받침 방향 모두 평가)
 → S6 결정론적 3단계 게이트(CONTRADICTED/CORROBORATED/UNVERIFIED) + 2단 가드레일 → 판정
```

각 단계 코드 상단에 "왜 이 순서인가"가 주석으로 남아 있습니다 (`counter/pipeline/`).

## 실행 (로컬)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # 실제 값 입력 (커밋 금지)
streamlit run app.py
```

앱 첫 부팅 시 마이그레이션(Neon PostgreSQL + pgvector)과 업종 centroid 임베딩 시드가
**자동으로 멱등 실행**됩니다 (`counter/bootstrap.py`). 수동 실행이 필요하면
`python -m scripts.migrate`, `python -m scripts.seed_categories`.

- 메인 화면: 입력 → 판정 결과 (+ 판정 후 비동기 👍/👎 피드백)
- **Raw Trace** 페이지: `tool.call`/`tool.result` 무가공 스트림 (대회 규칙 3 — 세컨드 화면)
- **Stats** 페이지: 게이트 통과율·캐시 재사용·델타 절감·판정 분포

## 배포 (Streamlit Community Cloud)

1. 이 리포를 GitHub에 push (public)
2. [share.streamlit.io](https://share.streamlit.io) → **Deploy a public app from GitHub** →
   리포 선택, main 브랜치, entrypoint `app.py`
3. 앱 설정 → **Secrets**에 `.streamlit/secrets.toml.example` 내용을 붙여넣고 실제 값 입력
   (`OPENAI_API_KEY`, `LINER_API_KEY`, Neon의 `DATABASE_URL` — pooled connection string 권장)
4. 재시작하면 첫 부팅에서 스키마/시드가 자동 적용됨

⚠️ LINER 엔드포인트/파라미터는 실측 전 미확인 상태입니다 (`MODELS_AND_APIS.md` §3.2).
실측 후 Secrets의 `LINER_API_BASE`/`LINER_*_PATH`/`LINER_SUPPORTS_DATE_FILTER`만 수정하면
됩니다 (코드 변경 불필요). 날짜필터 미지원 시 델타 서치는 자동으로 스코프 아웃되고
캐시는 fresh/full 2-state로 동작합니다.

## 테스트

```bash
pytest
```

핵심은 **T2 — 필수 필드 미충족 candidate가 CONTRADICTED/CORROBORATED로 승격되지 않음**.
사람 검수 단계가 설계상 없으므로 이 테스트가 유일한 정확성 보증입니다 (`tests/`).

## 문서

설계 근거 전체는 기획 문서(PRD/ARCHITECTURE/DECISIONS/…)를 따릅니다.
되돌리면 안 되는 결정들(사람 승인 단계 폐기, 신뢰도 점수 미제공, pgvector 통일,
검색은 전부 LINER 등)은 DECISIONS.md 기준입니다.

⚠️ 순위·AI 성능 광고 사전실증 관련 공정위 「표시·광고 실증에 관한 운영」 개정안은
2026-08-01 기준 **행정예고 상태이며 최종 시행 여부는 미확인**입니다.
