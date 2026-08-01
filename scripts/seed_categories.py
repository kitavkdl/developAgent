"""업종 카테고리 centroid 임베딩 시드 (로컬/수동 실행용): python -m scripts.seed_categories

Streamlit Cloud 배포에서는 앱 첫 부팅 시 counter/bootstrap.py가 같은 작업을
자동으로 수행하므로 이 스크립트는 로컬 개발 편의용이다.

카테고리 임베딩과 claim 임베딩은 반드시 같은 모델(text-embedding-3-small)을 쓴다 —
섞으면 유사도가 무의미 (MODELS_AND_APIS §2.2).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from counter.bootstrap import run_bootstrap  # noqa: E402
from counter.clients.openai_client import OpenAIClient  # noqa: E402
from counter.db import Db  # noqa: E402
from counter.settings import load_settings  # noqa: E402


def main() -> None:
    settings = load_settings()
    result = run_bootstrap(Db(settings), OpenAIClient(settings), settings)
    print(f"마이그레이션 적용 완료, centroid 시드 {result['centroids_seeded']}건")


if __name__ == "__main__":
    main()
