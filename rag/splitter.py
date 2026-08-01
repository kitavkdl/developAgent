"""
rag/splitter.py

AI Secretary Pro V1.0
"""

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentSplitter:

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(
        self,
        documents: List[Document],
    ) -> List[Document]:

        chunks = self.splitter.split_documents(documents)

        print(f"원본 문서 : {len(documents)}")
        print(f"Chunk 수 : {len(chunks)}")

        return chunks


if __name__ == "__main__":

    from rag.loader import DocumentLoader

    loader = DocumentLoader()

    docs = loader.load_all_pdfs()

    splitter = DocumentSplitter()

    chunks = splitter.split(docs)

    print(chunks[0].page_content[:300])