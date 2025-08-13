# app/report.py
import json
from typing import List, Dict, Any

def build_report(answers: List[Dict[str, Any]]):
    """
    Build markdown and JSON reports from a list of answers.
    Each answer is a dict with keys: question, route, answer, evidence, etc.
    """
    lines = ["# Run Report", ""]
    for a in answers:
        lines.append(f"## Question")
        lines.append(a["question"])
        lines.append("")
        lines.append(f"- Route: {a['route']}")
        lines.append("")
        lines.append("### Answer")
        lines.append(a["answer"])
        lines.append("")
        lines.append("### Evidence")
        lines.append(json.dumps(a.get("evidence", {}), indent=2, ensure_ascii=False))
        lines.append("")
    report_md = "\n".join(lines)
    report_json = json.dumps(answers, indent=2, ensure_ascii=False)
    return report_md, report_json
