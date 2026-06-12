import json
import sys
import tempfile
import time
from pathlib import Path

from .helpers import load_case_metadata
from .registry import EVALS

from .report import build_report
def main():
    results = []
    case_metadata = load_case_metadata()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        for eval_id, test_func in EVALS:
            started = time.monotonic()
            metadata = case_metadata.get(eval_id, {})
            try:
                test_func(tmp_root)
                results.append(
                    {
                        "id": eval_id,
                        "status": "pass",
                        "description": metadata.get("description", ""),
                        "score": 1.0,
                        "duration_seconds": round(time.monotonic() - started, 3),
                        "findings": [],
                        "recommended_actions": [],
                    }
                )
            except Exception as error:
                message = str(error)
                results.append(
                    {
                        "id": eval_id,
                        "status": "fail",
                        "description": metadata.get("description", ""),
                        "score": 0.0,
                        "duration_seconds": round(time.monotonic() - started, 3),
                        "findings": [message],
                        "recommended_actions": [
                            f"Reproduce `{eval_id}` locally with python3 skills/harness-engine/evals/run_evals.py.",
                            "Treat the failing assertion as the next implementation input before release.",
                        ],
                    }
                )

    report = build_report(results)
    print(json.dumps(report, indent=2) + "\n")
    if report["status"] != "pass":
        sys.exit(1)

