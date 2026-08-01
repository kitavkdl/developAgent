"""
rag/loader.py

AI Secretary Pro V1.0
"""

from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

from config.settings import settings


class DocumentLoader:
    """PDF 문서를 로드하는 클래스"""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or settings.DATA_DIR

    def load_pdf(self, pdf_path: str | Path) -> List[Document]:
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"{pdf_path} 파일을 찾을 수 없습니다.")

        print(f"📄 {pdf_path.name}")

        loader = PyPDFLoader(str(pdf_path))

        return loader.load()

    def load_all_pdfs(self) -> List[Document]:

        documents: List[Document] = []

        pdf_files = sorted(self.data_dir.glob("*.pdf"))

        if not pdf_files:
            raise FileNotFoundError(
                f"{self.data_dir} 폴더에 PDF가 없습니다."
            )

        for pdf in pdf_files:
            documents.extend(self.load_pdf(pdf))

        print(f"\n총 {len(documents)} 페이지 로드 완료")

        return documents


if __name__ == "__main__":

    loader = DocumentLoader()

    docs = loader.load_all_pdfs()

    print("=" * 60)
    print(f"총 문서 수 : {len(docs)}")
    print("=" * 60)