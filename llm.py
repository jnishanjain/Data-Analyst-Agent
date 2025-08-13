import os
import time
import json
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()  # Load .env if present

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.disabled = not bool(self.api_key)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: Optional[int] = 300) -> str:
        if self.disabled:
            return ""
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

        retries = 3
        delay = 1
        for attempt in range(retries):
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=30)
                if r.status_code in (429,) or 500 <= r.status_code < 600:
                    time.sleep(delay)
                    delay *= 2
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception:
                if attempt == retries - 1:
                    return ""
        return ""

    def classify_route(self, question: str, has_csv: bool, csv_columns: Optional[List[str]]) -> str:
        if self.disabled:
            cues = ["in the dataset", "in the csv", "average", "count", "top", "group", "mean", "sum", "unique", "by "]
            return "csv" if has_csv and any(c in question.lower() for c in cues) else "web"
        sys = "You decide if a question should be answered using a CSV dataset or by searching the web. Answer with 'csv' or 'web'."
        user = f"Question: {question}\nHas CSV: {has_csv}\nColumns: {csv_columns}"
        out = self.chat([{"role": "system", "content": sys}, {"role": "user", "content": user}], temperature=0.0, max_tokens=5)
        return "csv" if "csv" in out.lower() else "web" if out else "web"

    def map_to_csv_plan(self, question: str, csv_columns: List[str]) -> Optional[Dict[str, Any]]:
        if self.disabled:
            return None
        sys = "Map the question to a pandas op. Return JSON with keys: kind, col/by/metric/agg/k/ascending if needed."
        user = f"Question: {question}\nColumns: {csv_columns}"
        out = self.chat([{"role": "system", "content": sys}, {"role": "user", "content": user}], temperature=0.0, max_tokens=200)
        try:
            return json.loads(out) if out else None
        except Exception:
            return None

    def phrase_csv_answer(self, question: str, summary: str, metrics: Dict[str, Any]) -> str:
        if self.disabled:
            return summary
        sys = "Rewrite the data result into a concise 1-2 sentence answer."
        user = f"Question: {question}\nResult: {summary}\nMetrics: {metrics}"
        out = self.chat([{"role":"system","content":sys}, {"role":"user","content":user}], temperature=0.3, max_tokens=150)
        return out.strip() if out else summary

    def phrase_web_answer(self, question: str, snippets: List[str], sources: List[str]) -> str:
        if self.disabled:
            return f"Synthesized from {len(sources)} sources." if sources else "No sources found."
        sys = "Write a 2-4 sentence answer using only the provided snippets. Cite sources as [1], [2]..."
        joined = "\n\n".join(snippets[:3]) if snippets else "No snippets."
        user = f"Question: {question}\nSnippets:\n{joined}"
        out = self.chat([{"role":"system","content":sys}, {"role":"user","content":user}], temperature=0.2, max_tokens=220)
        return out.strip() if out else f"Synthesized from {len(sources)} sources."
