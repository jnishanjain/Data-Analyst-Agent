import pandas as pd
from typing import Dict, Any

def execute_plan(plan: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    if plan["kind"] == "count_rows":
        return {"summary": f"Total rows: {len(df)}", "metrics": {"rows": len(df)}}
    if plan["kind"] == "nunique":
        col = plan["col"]
        n = df[col].nunique()
        return {"summary": f"Unique values in {col}: {n}", "metrics": {"col": col, "nunique": n}}
    if plan["kind"] == "topk":
        col, k, asc = plan["col"], plan["k"], plan["ascending"]
        sub = df[[col]].dropna().sort_values(col, ascending=asc).head(k)
        return {"summary": f"Top {k} by {col}", "metrics": {"col": col, "k": k}, "preview": sub[col].tolist()}
    raise ValueError(f"Unknown plan: {plan}")
