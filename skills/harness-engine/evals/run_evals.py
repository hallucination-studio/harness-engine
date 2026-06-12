#!/usr/bin/env python3

from pathlib import Path
import sys

EVALS_DIR = Path(__file__).resolve().parent
if str(EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(EVALS_DIR))

from harness_engine_evals.runner import main


if __name__ == "__main__":
    main()
