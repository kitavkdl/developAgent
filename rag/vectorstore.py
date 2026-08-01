"""
rag/vectorstore.py

AI Secretary Pro V1.0
"""

from pathlib import Path

from langchain_chroma import Chroma

from config.settings import settings
from llm.model import get_embeddings
from rag.loader import DocumentLoader
from rag.splitter import DocumentSplitter


class VectorStoreManager:
    """
    ChromaDB Manager
    """

    def __init__(self):

        self.embedding = get_embeddings()

        self.persist_directory = str(settings.VECTOR_DB_DIR)

    # ----------------------------------------

    def build_vectorstore(self):

        print("=" * 60)
        print("📄 PDF Loading...")
        print("=" * 60)

        loader = DocumentLoader()

        documents = loader.load_all_pdfs()

        if not documents:
            raise ValueError("data 폴더에 PDF가 없습니다.")

        print()

        print("=" * 60)
        print("✂️ Split Documents")
        print("=" * 60)

        splitter = DocumentSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )

        chunks = splitter.split(documents)

        print()

        print("=" * 60)
        print("🧠 Embedding...")
        print("=" * 60)

        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding,
            persist_directory=self.persist_directory,
        )

        print()

        print("=" * 60)
        print("✅ ChromaDB 생성 완료")
        print("=" * 60)

        return vectordb

    # ----------------------------------------

    def load_vectorstore(self):

        return Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embedding,
        )

    # ----------------------------------------

    def get_vectorstore(self):

        db_path = Path(self.persist_directory)

        if db_path.exists() and any(db_path.iterdir()):

            print("📂 기존 VectorDB 사용")

            return self.load_vectorstore()

        print("🆕 새로운 VectorDB 생성")

        return self.build_vectorstore()

    # ----------------------------------------

    def get_retriever(self, k=4):

        db = self.get_vectorstore()

        return db.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": k
            }
        )


if __name__ == "__main__":

    manager = VectorStoreManager()

    retriever = manager.get_retriever()

    print()

    print("=" * 60)
    print("Retriever 생성 완료")
    print("=" * 60)

    print(retriever)