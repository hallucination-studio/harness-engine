def build_report(results):
    passed = sum(1 for result in results if result["status"] == "pass")
    total = len(results)
    failed_results = [result for result in results if result["status"] == "fail"]
    return {
        "schema_version": "harness-eval-report.v1",
        "status": "pass" if passed == total else "fail",
        "score": round((passed / total) * 100) if total else 0,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "message": (
                f"All {total} harness eval cases passed."
                if passed == total
                else f"{total - passed} of {total} harness eval cases failed."
            ),
        },
        "metrics": {
            "case_pass_rate": round(passed / total, 4) if total else 0,
            "case_fail_rate": round((total - passed) / total, 4) if total else 0,
            "failed_case_count": total - passed,
        },
        "case_results": results,
        "user_message": (
            "Harness evals passed. No release-blocking eval findings were detected."
            if passed == total
            else "Harness evals failed. Review `case_results` and fix the listed findings before handoff or release."
        ),
        "recommended_actions": [
            action
            for result in failed_results
            for action in result["recommended_actions"]
        ],
    }

