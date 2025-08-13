import json
from typing import List, Dict, Any, Tuple

def build_report(answers: List[Dict[str, Any]]) -> Tuple[str, str]:
    # Build the per-question files payload (array of arrays)
    payload = []
    for a in answers:
        files = a.get("files")
        if files is None:
            content = {
                "question": a.get("question", ""),
                "route": a.get("route", ""),
                "answer": a.get("answer", ""),
                "evidence": a.get("evidence", None),
            }
            files = [{
                "name": "report.json",
                "type": "application/json",
                "data": json.dumps(content, ensure_ascii=False, separators=(",", ":")),
            }]
        if not isinstance(files, list):
            raise TypeError("Per-question files must be a list")
        for f in files:
            if not isinstance(f, dict):
                raise TypeError("Each file must be an object")
            for k in ("name", "type", "data"):
                if k not in f or not isinstance(f[k], str):
                    raise TypeError("File fields 'name','type','data' must be present and strings")
        payload.append(files)

    # Value 1: markdown (empty or keep your previous markdown report)
    report_md = ""
    # Value 2: JSON string for backward compatibility with existing callers
    report_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return report_md, report_json
