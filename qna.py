import re
import pandas as pd
from typing import List, Dict, Any

QUESTION_RE = re.compile(r"([^\n?.!]*\?)(?:\s|$)")

def extract_questions(text: str) -> List[str]:
    qs = [m.group(1).strip() for m in QUESTION_RE.finditer(text)]
    seen, out = set(), []
    for q in qs:
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out

def classify_question(q: str, has_csv: bool) -> str:
    cues = [
        "in the dataset", "in the csv", "average", "count", "top", "group", "mean", "sum", "unique",
        "by ", "total", "sales", "tax", "median", "max", "min", "correlation", "plot", "chart", "graph"
    ]
    return "csv" if has_csv and any(c in q.lower() for c in cues) else "web"


def plan_csv_op(q: str, df: pd.DataFrame) -> Dict[str, Any]:
    ql = q.lower()
    if "row" in ql and "count" in ql:
        return {"kind": "count_rows"}
    if "unique" in ql:
        for col in df.columns:
            if col.lower() in ql:
                return {"kind": "nunique", "col": col}
    if "top" in ql:
        return {"kind": "topk", "col": df.columns[0], "k": 5, "ascending": False}
    return {"kind": "count_rows"}
