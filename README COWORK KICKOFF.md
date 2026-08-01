# Cowork 첫 세션에 붙여넣을 킥오프 프롬프트

> 아래 블록을 그대로 복사해서 Cowork(Fable 5) 첫 메시지로 보내세요.
> 문서 7개는 같은 폴더에 함께 업로드/연결되어 있어야 합니다.

---

```
COUNTER라는 AI 에이전트를 함께 개발합니다. 24시간 해커톤 제출물이고, 시간이 매우 촉박합니다.

먼저 다음 순서로 문서를 읽어주세요. 읽기 전에 코드를 작성하지 마세요.

1. PRD.md         — 제품 정의와 불가침 규칙. 여기가 단일 진실 원천입니다.
2. DECISIONS.md   — 왜 이렇게 설계됐는지. 되돌리면 안 되는 것들이 적혀 있습니다.
3. ARCHITECTURE.md — 파이프라인 단계와 각 단계가 그 위치에 있는 이유
4. MODELS_AND_APIS.md — 어떤 모델을 어디에 쓰는지, API 연동 명세
5. DB_SCHEMA.md   — 스키마와 캐시 로직, REFUTED 게이트
6. PROMPTS.md     — 각 에이전트의 시스템 프롬프트
7. BUILD_PLAN.md  — 작업 순서와 검증 게이트

읽은 뒤 다음을 먼저 해주세요.

(a) 문서들 사이에 서로 모순되는 부분이 있으면 지적해주세요. 코드로 넘어가기 전에
    제가 정리하겠습니다.

(b) PRD.md §4의 불가침 규칙 6개를 당신 말로 요약해주세요. 특히 N1(결정론적 REFUTED
    게이트)과 N2(사람이 판정을 게이트하지 않음)를 정확히 이해했는지 확인하고 싶습니다.

(c) BUILD_PLAN.md §0의 실측 항목 중, 아직 확인 안 된 전제 위에 코드를 쌓으면 나중에
    통째로 버려야 하는 것이 무엇인지 알려주세요.

그 다음 BUILD_PLAN.md §2의 B01부터 순서대로 진행합니다. 각 단계의 검증 게이트를
통과했는지 확인하고 다음으로 넘어가주세요. "돌아가는 것 같다"로 넘어가지 마세요.

중요한 작업 원칙:
- 설계를 바꾸고 싶어지면 먼저 DECISIONS.md를 확인하세요. 이미 시도했다가 폐기한
  경로일 가능성이 높습니다. 그래도 바꿔야 한다고 판단되면 저에게 먼저 물어보세요.
- 임계값·모델ID·TTL·검색예산·타임아웃은 전부 설정으로 빼고 하드코딩하지 마세요.
- 커밋을 자주 남겨주세요. 커밋 히스토리 자체가 심사 대상입니다.
- 각 파이프라인 단계 코드 상단에 "왜 이 순서인가"를 주석으로 남겨주세요.
- 확실하지 않은 것을 확실한 것처럼 구현하지 마세요. 모르면 물어보세요.

배포/UI 관련 (중요, 기존 계획에서 변경됨):
- 이 프로젝트는 별도 프론트엔드 팀원 없이 Streamlit 단일 앱으로 배포합니다.
  즉, 이 세션에서 백엔드 파이프라인뿐 아니라 Streamlit UI(입력 화면, 판정 결과 렌더링,
  대회 규칙상 필수인 raw tool_call/tool_result 세컨드 화면, 통계 대시보드)까지 전부
  만들어야 합니다. PRD.md §9와 BUILD_PLAN.md §1(개정판)을 참고하세요.
- DB는 Neon(PostgreSQL + pgvector)을 씁니다. 배포 경로는 로컬 개발 → GitHub →
  Streamlit Community Cloud입니다.
- 세컨드 화면(raw stream)은 HTTP SSE가 아니라 Neon의 trace_event 테이블을 폴링하는
  방식으로 구현합니다 (BUILD_PLAN.md §1 참조). 별도 REST API 서버를 새로 세우지 마세요.
- 리포는 public입니다 (Streamlit Community Cloud의 "Deploy a public app from GitHub"
  경로를 씁니다). 그래서 가장 먼저 할 일은 .gitignore를 커밋하는 것입니다. API 키·DB
  연결 문자열은 코드에 절대 쓰지 말고 .streamlit/secrets.toml(로컬)과 Streamlit Cloud
  Secrets(배포)에만 넣습니다. 템플릿은 .streamlit/secrets.toml.example을 보세요.
  MODELS_AND_APIS.md §2.5 참고.
```

---

## 문서 목록 체크리스트

Cowork 세션에 아래 7개가 전부 있어야 합니다.

- [ ] `PRD.md`
- [ ] `ARCHITECTURE.md`
- [ ] `MODELS_AND_APIS.md`
- [ ] `DB_SCHEMA.md`
- [ ] `PROMPTS.md`
- [ ] `DECISIONS.md`
- [ ] `BUILD_PLAN.md`

## 업로드하지 말아야 할 것

이전 기획 과정에서 만들어진 아래 문서들은 **구버전이라 Cowork에 주면 혼란을 일으킵니다.** 넣지 마세요.

- 사람이 반례를 승인하는 구조가 남아 있는 ERD 초안 (D-01에서 폐기됨)
- SQLite + FAISS를 전제한 빌드 프롬프트 (D-06에서 pgvector로 변경됨)
- "2026년 6월 1일부터 순위광고 실증 의무 시행"이라고 쓰인 문서 (D-10, 사실관계 오류)
- OpenAI web_search를 GENERAL 경로에 쓰는 설계 (D-04에서 변경됨)
- **별도 팀원이 프론트엔드를 만든다는 전제로 짜인 구버전 인터페이스 계약** (D-14에서 Streamlit 단일 배포로 변경됨)

위 7개 문서에 최신 결정이 전부 반영되어 있습니다.
