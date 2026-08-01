"""
assistant.py

AI Secretary Pro V1.0
"""

from langchain_core.messages import HumanMessage

from llm.model import llm
from memory.chat_memory import memory

from tools.current_time import current_time
from tools.document_info import document_info
from tools.pdf_search import pdf_search


class Assistant:
    """AI 비서"""

    def __init__(self):
        self.llm = llm

    # --------------------------------------------------

    def ask(self, question: str) -> str:

        q = question.lower()

        # -----------------------------
        # 현재 시간
        # -----------------------------
        if "시간" in q or "날짜" in q:

            answer = current_time.invoke({})

        # -----------------------------
        # PDF 목록
        # -----------------------------
        elif "문서" in q or "pdf" in q:

            answer = document_info.invoke({})

        # -----------------------------
        # 회사 규정
        # -----------------------------
        elif (
            "연차" in q
            or "규정" in q
            or "휴가" in q
            or "출장" in q
            or "회사" in q
        ):

            answer = pdf_search.invoke(
                {
                    "question": question
                }
            )

        # -----------------------------
        # GPT
        # -----------------------------
        else:

            messages = memory.messages()

            messages.append(
                HumanMessage(content=question)
            )

            response = self.llm.invoke(messages)

            answer = response.content

        # -----------------------------

        memory.add_user(question)

        memory.add_ai(answer)

        return answer


assistant = Assistant()


# ----------------------------------------------------------

if __name__ == "__main__":

    print("=" * 60)
    print(" AI Secretary Pro ")
    print("=" * 60)

    while True:

        question = input("\n질문(q 종료): ")

        if question.lower() == "q":
            break

        print()

        print(assistant.ask(question))