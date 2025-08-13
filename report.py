import json
from typing import List, Dict, Any

def build_report(answers: List[Dict[str, Any]]):
    lines = ["# Run Report", ""]
    for a in answers:
        lines.append(f"## Question: {a['question']}")
        lines.append(f"- Route: {a['route']}")
        lines.append(f"- Answer: {a['answer']}")
        lines.append(f"- Evidence: {json.dumps(a.get('evidence', {}), indent=2, ensure_ascii=False)}")
        lines.append("")
    return "\n".join(lines), json.dumps(answers, indent=2, ensure_ascii=False)
