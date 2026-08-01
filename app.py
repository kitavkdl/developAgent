"""
app.py

AI Secretary Pro V1.0
"""

import streamlit as st

from graph.workflow import workflow
from memory.chat_memory import memory
from tools.document_info import document_info

# -----------------------------------------

st.set_page_config(
    page_title="AI Secretary Pro",
    page_icon="🤖",
    layout="wide",
)

# -----------------------------------------

st.title("🤖 AI Secretary Pro")

st.caption("OpenAI + LangChain + RAG + LangGraph")

# -----------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------------------
# Sidebar
# -----------------------------------------

with st.sidebar:

    st.header("📂 프로젝트")

    if st.button("🗑 대화 초기화"):

        st.session_state.messages = []

        memory.clear()

        st.success("대화가 초기화되었습니다.")

    st.divider()

    st.subheader("등록된 PDF")

    st.text(document_info.invoke({}))

    st.divider()

    st.info(
        """
AI Secretary Pro V1.0

• OpenAI
• LangChain
• LangGraph
• ChromaDB
• RAG
        """
    )

# -----------------------------------------
# 이전 대화 출력
# -----------------------------------------

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])

# -----------------------------------------
# 질문 입력
# -----------------------------------------

question = st.chat_input("질문을 입력하세요...")

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):

        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("생각하는 중..."):

            result = workflow.invoke(
                {
                    "question": question,
                    "answer": "",
                }
            )

            answer = result["answer"]

            st.markdown(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )