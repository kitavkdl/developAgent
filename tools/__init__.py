from .calculator import calculator
from .current_time import current_time
from .web_search import web_search
from .pdf_search import pdf_search
from .document_info import document_info

TOOLS = [
    calculator,
    current_time,
    web_search,
    pdf_search,
    document_info,
]


def get_tools():
    return TOOLS