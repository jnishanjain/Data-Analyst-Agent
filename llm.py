import os
from typing import Optional, Dict, Any, List

# Minimal, dependency-light HTTP client using requests to avoid hard SDK coupling.
import requests

class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not self.api_key:
            # Operate in no-LLM mode with graceful fallbacks.
            self.disabled = True
        else:
            self.disabled = False

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: Optional[int] = 300) -> str:
        if self.disabled:
            # Fallback: return empty string; callers should handle gracefully.
            return ""
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

    # High-level helpers

    def classify_route(self, question: str, has_csv: bool, csv_columns: Optional[List[str]]) -> str:
        if self.disabled:
            # Heuristic fallback: if CSV exists and question mentions typical cues, pick CSV.
            cues = ["in the dataset", "in the csv", "according to the data",
                    "average", "count", "top", "group", "trend", "correlation",
                    "mean", "sum", "median", "min", "max", "unique", "by "]
            if has_csv and any(c in question.lower() for c in cues):
                return "csv"
            return "web"

        sys = "You decide if a question should be answered using a CSV dataset or by searching the web. Respond with exactly 'csv' or 'web'."
        cols_str = ", ".join(csv_columns or [])
        user = f"Question: {question}\nHas CSV: {has_csv}\nCSV columns: [{cols_str}]\nAnswer only csv or web."
        out = self.chat([{"role":"system","content":sys},{"role":"user","content":user}], temperature=0.0, max_tokens=5).strip().lower()
        return "csv" if "csv" in out else "web"

    def map_to_csv_plan(self, question: str, csv_columns: List[str]) -> Optional[Dict[str, Any]]:
        if self.disabled:
            return None
        sys = (
            "Map the question to a simple pandas plan JSON for one of: "
            "count_rows | nunique(col) | groupby_agg(by, metric, agg in {mean,sum,count}) | topk(col,k,ascending=false). "
            "Return ONLY JSON. If impossible, return null."
        )
        user = f"Question: {question}\nColumns: {csv_columns}"
        out = self.chat([{"role":"system","content":sys},{"role":"user","content":user}], temperature=0.0, max_tokens=200)
        # Be defensive parsing. If JSON fails, caller falls back to heuristic plan.
        try:
            import json
            plan = json.loads(out)
            if isinstance(plan, dict):
                return plan
        except Exception:
            pass
        return None

    def phrase_csv_answer(self, question: str, summary: str, metrics: Dict[str, Any]) -> str:
        if self.disabled:
            return summary
        sys = "Rewrite the data analysis result into a concise 1-2 sentence answer. Be precise and avoid speculation."
        user = f"Question: {question}\nResult summary: {summary}\nMetrics: {metrics}"
        out = self.chat([{"role":"system","content":sys},{"role":"user","content":user}], temperature=0.3, max_tokens=150)
        return out.strip()

    def phrase_web_answer(self, question: str, snippets: List[str], sources: List[str]) -> str:
        if self.disabled:
            if sources:
                return f"Synthesized from {len(sources)} sources. See evidence."
            return "No reliable sources fetched."
        joined = "\n\n".join(snippets[:3]) if snippets else "No snippets."
        sys = (
            "Write a concise 2-4 sentence answer grounded ONLY in the provided snippets. "
            "If uncertain, say so. Avoid fabricating facts."
        )
        user = f"Question: {question}\nSnippets:\n{joined}\nCite the source numbers inline like [1], [2] corresponding to the order of the sources list."
        out = self.chat([{"role":"system","content":sys},{"role":"user","content":user}], temperature=0.2, max_tokens=220)
        return out.strip()
