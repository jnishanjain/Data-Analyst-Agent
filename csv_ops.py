import pandas as pd
import matplotlib.pyplot as plt
import base64
import io
from typing import Dict, Any

def _plot_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    data = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{data}"

def execute_plan(plan: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    kind = plan.get("kind")
    try:
        if kind == "count_rows":
            return {"summary": f"Total rows: {len(df)}", "metrics": {"rows": len(df)}}

        if kind == "sum":
            col = plan["col"]
            total = df[col].sum()
            return {"summary": f"Total {col}: {total}", "metrics": {"total": total}}

        if kind == "group_sum_top":
            group_col, sum_col = plan["group_col"], plan["sum_col"]
            grouped = df.groupby(group_col)[sum_col].sum()
            top_val = grouped.idxmax()
            return {"summary": f"Top {group_col}: {top_val}", "metrics": {"top": top_val}}

        if kind == "correlation":
            col_x, col_y = plan["col_x"], plan["col_y"]
            corr = df[col_x].corr(df[col_y])
            return {"summary": f"Correlation between {col_x} and {col_y}: {corr:.3f}", "metrics": {"correlation": corr}}

        if kind == "median":
            col = plan["col"]
            med = df[col].median()
            return {"summary": f"Median {col}: {med}", "metrics": {"median": med}}

        if kind == "bar_chart":
            fig, ax = plt.subplots()
            df.groupby(plan["x"])[plan["y"]].sum().plot(kind="bar", ax=ax)
            img = _plot_to_base64(fig)
            return {"summary": "Generated bar chart.", "metrics": {"chart": img}}

        if kind == "line_chart":
            fig, ax = plt.subplots()
            temp = df.copy()
            temp[plan["x"]] = pd.to_datetime(temp[plan["x"]], errors="coerce")
            temp = temp.dropna(subset=[plan["x"]])
            temp = temp.sort_values(plan["x"])
            ax.plot(temp[plan["x"]], temp[plan["y"]])
            img = _plot_to_base64(fig)
            return {"summary": "Generated line chart.", "metrics": {"chart": img}}

        return {"summary": "Plan not recognized.", "metrics": {}}

    except Exception as e:
        return {"summary": f"Could not execute plan: {str(e)}", "metrics": {}}
