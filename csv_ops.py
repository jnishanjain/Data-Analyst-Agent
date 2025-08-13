from typing import Dict, Any
import pandas as pd

def execute_plan(plan: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    kind = plan["kind"]

    if kind == "count_rows":
        n = int(len(df))
        return {
            "summary": f"Total rows: {n}.",
            "metrics": {"rows": n}
        }

    if kind == "nunique":
        col = plan["col"]
        n = int(df[col].nunique(dropna=True))
        return {
            "summary": f"Unique values in {col}: {n}.",
            "metrics": {"col": col, "nunique": n},
            "preview": df[col].dropna().unique()[:10].tolist()
        }

    if kind == "groupby_agg":
        by = plan["by"]
        agg = plan["agg"]
        metric = plan.get("metric")
        if agg == "count":
            s = df.groupby(by).size().sort_values(ascending=False)
        else:
            if metric is None:
                raise ValueError("metric column required for mean/sum")
            if agg == "mean":
                s = df.groupby(by)[metric].mean().sort_values(ascending=False)
            elif agg == "sum":
                s = df.groupby(by)[metric].sum().sort_values(ascending=False)
            else:
                raise ValueError(f"Unsupported agg: {agg}")
        top = s.head(10)
        return {
            "summary": f"{agg} by {by}" + (f" of {metric}" if metric else "") + f": top {len(top)} shown.",
            "metrics": {"agg": agg, "by": by, "metric": metric},
            "preview": top.reset_index().to_dict(orient="records")
        }

    if kind == "topk":
        col = plan["col"]
        k = plan["k"]
        asc = plan.get("ascending", False)
        sub = df[[col]].dropna().sort_values(col, ascending=asc).head(k)
        return {
            "summary": f"Top {len(sub)} by {col} ({'asc' if asc else 'desc'}).",
            "metrics": {"col": col, "k": k, "ascending": asc},
            "preview": sub[col].tolist()
        }

    raise ValueError(f"Unknown plan: {kind}")
