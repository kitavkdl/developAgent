"""
rag/retriever.py

AI Secretary Pro V1.0
"""

from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from rag.vectorstore import VectorStoreManager


class RetrieverManager:
    """
    Retriever Manager
    """

    def __init__(self):

        self.vectorstore = VectorStoreManager().get_vectorstore()

    # ------------------------------------------------

    def similarity(self, k: int = 4) -> BaseRetriever:

        return self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": k
            }
        )

    # ------------------------------------------------

    def mmr(self, k: int = 4) -> BaseRetriever:

        return self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": k,
                "fetch_k": 20
            }
        )

    # ------------------------------------------------

    def similarity_score(
        self,
        score: float = 0.6,
    ) -> BaseRetriever:

        return self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "score_threshold": score
            }
        )

    # ------------------------------------------------

    def search(
        self,
        query: str,
        search_type: str = "similarity",
        k: int = 4,
    ) -> List[Document]:

        if search_type == "mmr":

            retriever = self.mmr(k)

        elif search_type == "score":

            retriever = self.similarity_score()

        else:

            retriever = self.similarity(k)

        return retriever.invoke(query)


if __name__ == "__main__":

    manager = RetrieverManager()

    docs = manager.search(
        "연차는 몇 개인가요?"
    )

    print("=" * 60)

    print(f"검색 결과 : {len(docs)}")

    print("=" * 60)

    for idx, doc in enumerate(docs, start=1):

        print(f"\n[{idx}]")

        print(doc.page_content[:500])

        print("-" * 60)