"""
tools/pdf_search.py

RAG Search Tool
"""

from langchain_core.tools import tool

from rag.retriever import RetrieverManager


retriever = RetrieverManager()


@tool
def pdf_search(question: str) -> str:
    """
    회사 문서(PDF)를 검색합니다.

    사용 예시
    ----------
    pdf_search("연차 규정을 알려줘")
    """

    docs = retriever.search(
        question,
        search_type="similarity",
        k=4,
    )

    if not docs:
        return "관련 문서를 찾지 못했습니다."

    answer = []

    for idx, doc in enumerate(docs, start=1):

        answer.append(
            f"[{idx}]\n{doc.page_content}"
        )

    return "\n\n".join(answer)


if __name__ == "__main__":

    print(
        pdf_search.invoke(
            {
                "question": "연차 규정"
            }
        )
    )