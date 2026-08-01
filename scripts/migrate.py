"""DB 마이그레이션 실행: python -m scripts.migrate

빈 Neon DB에 클린 적용 가능해야 함 (B01 검증 게이트). 멱등(IF NOT EXISTS / ON CONFLICT).
"""
from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from counter.db import Db  # noqa: E402
from counter.settings import load_settings  # noqa: E402


def main() -> None:
    settings = load_settings()
    db = Db(settings)
    files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "*.sql")))
    db.migrate(files)
    print(f"적용 완료: {len(files)}개 파일")
    for f in files:
        print(" -", os.path.basename(f))


if __name__ == "__main__":
    main()
