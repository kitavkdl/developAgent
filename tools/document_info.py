"""
tools/document_info.py

Document Information Tool
"""

from pathlib import Path

from langchain_core.tools import tool

from config.settings import settings


@tool
def document_info() -> str:
    """
    data 폴더의 PDF 목록을 보여줍니다.
    """

    pdfs = sorted(
        settings.DATA_DIR.glob("*.pdf")
    )

    if not pdfs:

        return "등록된 PDF가 없습니다."

    result = []

    for pdf in pdfs:

        size = pdf.stat().st_size / 1024

        result.append(
            f"{pdf.name} ({size:.1f} KB)"
        )

    return "\n".join(result)


if __name__ == "__main__":

    print(document_info.invoke({}))