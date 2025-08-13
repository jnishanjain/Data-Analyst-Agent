from typing import Optional, Dict, Any, List, Tuple
import pandas as pd

from app.qna import extract_questions, classify_question as heuristic_classify, plan_csv_op as heuristic_plan
from app.csv_ops import execute_plan
from app.web import answer_via_web
from app.report import build_report
from app.llm import LLMClient

def process_inputs(questions_text: str, df: Optional[pd.DataFrame]) -> Tuple[List[str], List[Dict[str, Any]], str, str]:
    llm = LLMClient()
    questions = extract_questions(questions_text)
    answers = []

    for q in questions:
        # 1) Decide route (LLM if available; else heuristic)
        if llm.disabled:
            route = heuristic_classify(q, df is not None)
        else:
            route = llm.classify_route(q, df is not None, list(df.columns) if df is not None else [])

        # 2) CSV route
        if route == "csv" and df is not None:
            # Plan via LLM; fallback to heuristic
            plan = None
            if not llm.disabled:
                plan = llm.map_to_csv_plan(q, list(df.columns))
            if not plan:
                plan = heuristic_plan(q, df)

            result = execute_plan(plan, df)
            final = llm.phrase_csv_answer(q, result["summary"], result.get("metrics", {}))
            answers.append({
                "question": q,
                "route": "csv",
                "steps": plan,
                "answer": final,
                "evidence": {"preview": result.get("preview"), "metrics": result.get("metrics")}
            })
        else:
            # 3) Web route
            web_result = answer_via_web(q)
            final = llm.phrase_web_answer(q, web_result.get("snippets", []), web_result.get("sources", []))
            answers.append({
                "question": q,
                "route": "web",
                "steps": web_result["queries"],
                "answer": final,
                "evidence": {"sources": web_result["sources"], "snippets": web_result["snippets"]}
            })

    report_md, report_json = build_report(answers)
    return questions, answers, report_md, report_json
