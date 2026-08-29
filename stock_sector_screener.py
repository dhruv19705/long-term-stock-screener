"""
Backward-compatible shim.

Prefer:
  from screener import run_evaluation
  python cli.py screen --sector both
  uvicorn api.main:app --reload
"""

from __future__ import annotations

import logging
import sys

from screener.pipeline import run_evaluation


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    max_workers = 8
    if len(argv) >= 2:
        try:
            max_workers = int(argv[1])
        except ValueError:
            pass
    df = run_evaluation(max_workers=max_workers)
    extra = {a.lower() for a in argv[2:]}
    if "summary" not in extra:
        print("\nFull results table:")
        print(df.to_string(index=False))
    else:
        print("\n(summary mode: full table omitted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
