# 🤖 AI Secretary Pro

OpenAI, LangChain, LangGraph, RAG를 활용하여 만든 **AI 비서 프로젝트**입니다.

본 프로젝트는 **ICT AI 활용 교육(80시간)**의 최종 개인 프로젝트로 제작되었습니다.

---

# 📌 프로젝트 소개

AI Secretary Pro는 회사에서 자주 사용하는 문서를 검색하고,
질문에 답변하며,
일반적인 AI 질의응답까지 가능한 **AI 비서 시스템**입니다.

주요 기술

- OpenAI GPT
- LangChain
- LangGraph
- RAG(Retrieval Augmented Generation)
- ChromaDB
- Streamlit

---

# 🚀 주요 기능

## ✅ 일반 AI 질의응답

예)

> 파이썬이 무엇인가요?

---

## ✅ 회사 규정 검색 (RAG)

예)

> 연차 규정을 알려줘

> 출장 규정을 알려줘

---

## ✅ PDF 문서 검색

data 폴더의 PDF를 검색하여 답변합니다.

---

## ✅ 현재 날짜 및 시간 조회

예)

> 오늘 날짜 알려줘

---

## ✅ 등록된 문서 확인

예)

> 등록된 문서를 보여줘

---

# 🛠 기술 스택

| 구분 | 기술 |
|------|------|
| Language | Python 3.12 |
| LLM | OpenAI GPT |
| Framework | LangChain |
| Workflow | LangGraph |
| Vector DB | ChromaDB |
| UI | Streamlit |
| Embedding | OpenAI Embedding |
| Search | DuckDuckGo |

---

# 📂 프로젝트 구조

```text
AI-Secretary-Pro/

app.py
assistant.py

config/
graph/
llm/
memory/
prompts/
rag/
tools/

data/
vector_db/
logs/

requirements.txt
README.md
.env.example
```

---

# ⚙ 실행 방법

## 1. 프로젝트 다운로드

```bash
git clone <repository>
```

---

## 2. 가상환경 생성

Windows

```bash
python -m venv .venv
```

활성화

```bash
.venv\Scripts\activate
```

---

## 3. 패키지 설치

```bash
pip install -r requirements.txt
```

---

## 4. 환경변수 설정

`.env.example`

↓

`.env`

복사

```env
OPENAI_API_KEY=본인의_API_KEY
```

---

## 5. 실행

```bash
streamlit run app.py
```

---

# 📄 테스트 질문

```
안녕하세요

오늘 날짜 알려줘

등록된 문서를 보여줘

연차 규정을 알려줘

출장 규정을 알려줘

파이썬이 무엇인가요?
```

---

# 💡 프로젝트 특징

- OpenAI API 연동
- LangChain 활용
- LangGraph Workflow 적용
- RAG 기반 PDF 검색
- Memory 기반 대화 유지
- Tool 활용
- Streamlit UI 제공

---

# 📚 향후 개선 사항

- PDF 업로드 기능
- 대화 저장 기능
- 음성 입력
- 이미지 분석
- 이메일 작성
- 일정 관리
- Multi Agent 지원

---

# 👨‍💻 개발 환경

- Python 3.12
- VS Code
- Windows 11

---

# 📜 License

MIT License

---

# 🙋 프로젝트 제작

AI Secretary Pro V1.0

OpenAI + LangChain + LangGraph 기반 AI 비서 프로젝트