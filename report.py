from typing import Optional, List, Any
import pandas as pd
from app.qna import extract_questions, classify_question, plan_csv_op
from app.csv_ops import execute_plan
from app.web import answer_via_web
from app.llm import LLMClient

def process_inputs(questions_text: str, df: Optional[pd.DataFrame]) -> List[str]:
    """
    Main orchestrator: returns flat list of answers.
    """
    llm = LLMClient()
    questions = extract_questions(questions_text)
    answers: List[str] = []

    for q in questions:
        route = classify_question(q, df is not None, list(df.columns) if df is not None else None)

        if route == "csv" and df is not None:
            plan = plan_csv_op(q, df)
            result = execute_plan(plan, df)
            final = llm.phrase_csv_answer(q, result["summary"], result.get("metrics", {})) \
                    if not llm.disabled else result["summary"]
            answers.append(final)

        else:
            web_result = answer_via_web(q)
            final = llm.phrase_web_answer(q, web_result.get("snippets", []), web_result.get("sources", [])) \
                    if not llm.disabled else web_result.get("synthesis", "No answer.")
            answers.append(final)

    return answers
