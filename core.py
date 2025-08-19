# app/core.py
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd

from app.qna import extract_questions, classify_question as heuristic_classify, plan_csv_op as heuristic_plan
from app.csv_ops import execute_plan
from app.web import scrape_website

from app.llm import LLMClient


def process_inputs(
    questions_text: str,
    df: Optional[pd.DataFrame] = None,
    url: Optional[str] = None
) -> Tuple[List[str], List[str]]:
    """
    Main orchestrator: classify, route to CSV or Web, get answers.
    Returns (questions, answers_list).
    """
    llm = LLMClient()
    questions = extract_questions(questions_text)
    answers: List[str] = []

    # If a URL is given, scrape it once
    scraped_text = scrape_website(url) if url else ""

    for q in questions:
        # --- Step 1: Classify route
        if llm.disabled:
            route = heuristic_classify(q, df is not None)
        else:
            route = llm.classify_route(q, df is not None, list(df.columns) if df is not None else None)

        # --- Step 2: CSV route
        if route == "csv" and df is not None:
            plan = heuristic_plan(q, df)
            if not llm.disabled:
                plan_llm = llm.map_to_csv_plan(q, list(df.columns))
                if plan_llm:
                    plan = plan_llm

            result = execute_plan(plan, df)
            final = llm.phrase_csv_answer(q, result["summary"], result.get("metrics", {})) \
                if not llm.disabled else result["summary"]
            answers.append(str(final))

        # --- Step 3: Web route
        else:
            context = scraped_text[:4000]  # truncate to avoid token limits
            final = llm.answer_with_context(q, context) if not llm.disabled else "No LLM available"
            answers.append(str(final))

    return questions, answers
