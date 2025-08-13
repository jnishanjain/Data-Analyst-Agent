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
    Core logic – takes the raw TXT content and optional DataFrame,
    returns the detected questions, answers array, and both report formats.
    """
    llm = LLMClient()
    questions = extract_questions(questions_text)
    answers = []

    for q in questions:
        # --- Decide route (CSV vs Web)
        route = heuristic_classify(q, df is not None)
        if not llm.disabled and df is not None and route == "web":
            # refine classification with LLM only if heuristic says "web" but CSV is available
            route = llm.classify_route(q, True, list(df.columns))

        # --- CSV route
        if route == "csv" and df is not None:
            plan = heuristic_plan(q, df)
            if not llm.disabled and plan.get("kind") == "count_rows" \
               and any(word in q.lower() for word in ["top", "mean", "sum", "average", "group", "unique"]):
                plan_llm = llm.map_to_csv_plan(q, list(df.columns))
                if plan_llm:
                    plan = plan_llm
            result = execute_plan(plan, df)
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
        else:
            # --- Web route
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

    report_md, report_json = build_report(answers)
    return questions, answers, report_md, report_json


