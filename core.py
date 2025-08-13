from typing import Optional, List, Dict, Any, Tuple
import pandas as pd

from app.qna import extract_questions, classify_question as heuristic_classify, plan_csv_op as heuristic_plan
from app.csv_ops import execute_plan
from app.web import answer_via_web
from app.report import build_report
from app.llm import LLMClient


def process_inputs(
    questions_text: str,
    df: Optional[pd.DataFrame]
) -> Tuple[List[str], List[Dict[str, Any]], str, str]:
    """
    Main orchestrator: reads questions, decides route (CSV/Web),
    runs appropriate analysis, and builds the final report.
    """
    llm = LLMClient()
    questions = extract_questions(questions_text)
    answers = []

    # Terms that strongly indicate CSV/data analysis
    data_terms = [
        "total", "sum", "average", "mean", "median", "top", "max", "min",
        "count", "unique", "group", "by ", "region", "sales", "correlation",
        "regression", "trend", "distribution", "percent", "ratio",
        "plot", "chart", "graph", "scatter", "bar", "line", "histogram"
    ]

    for q in questions:
        # --- Step 1: Decide route
        if df is not None:
            # Force CSV route if question clearly references data analysis or plotting
            if any(term in q.lower() for term in data_terms):
                route = "csv"
            else:
                # Fall back to heuristic if no strong data cues
                route = heuristic_classify(q, True)
        else:
            # No CSV → always web
            route = "web"

        # --- Step 2: CSV route
        if route == "csv" and df is not None:
            # Start with heuristic plan
            plan = heuristic_plan(q, df)

            # Let LLM refine plan if available
            if not llm.disabled:
                plan_llm = llm.map_to_csv_plan(q, list(df.columns))
                if plan_llm:
                    plan = plan_llm

            # Execute plan
            result = execute_plan(plan, df)

            # Phrase answer nicely
            final = llm.phrase_csv_answer(q, result["summary"], result.get("metrics", {})) \
                if not llm.disabled else result["summary"]

            answers.append({
                "question": q,
                "route": "csv",
                "steps": plan,
                "answer": final,
                "evidence": {
                    "preview": result.get("preview"),
                    "metrics": result.get("metrics")
                }
            })

        # --- Step 3: Web route
        else:
            web_result = answer_via_web(q)
            final = llm.phrase_web_answer(q, web_result.get("snippets", []), web_result.get("sources", [])) \
                if not llm.disabled else web_result["synthesis"]

            answers.append({
                "question": q,
                "route": "web",
                "steps": web_result["queries"],
                "answer": final,
                "evidence": {
                    "sources": web_result["sources"],
                    "snippets": web_result["snippets"]
                }
            })

    # --- Step 4: Build reports
    report_md, report_json = build_report(answers)
    return questions, answers, report_md, report_json
