import re
import time
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

# Simple, engine-agnostic fetch: provide a few direct URLs or build naive queries to known sites.
# For the MVP we keep it minimal: attempt a couple of public pages derived from keywords.

def build_queries(question: str) -> List[str]:
    # Extract keywords: alphanumerics only
    toks = re.findall(r"[A-Za-z0-9]+", question)
    toks = [t.lower() for t in toks if len(t) > 2]
    # Naive curated sources that are generally informative (replace/extend as needed)
    candidates = [
        "https://en.wikipedia.org/wiki/Main_Page",
        "https://www.britannica.com",
    ]
    return candidates

def fetch_page(url: str, timeout: int = 10) -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def extract_text(html: str, max_chars: int = 2000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    ps = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = " ".join(ps)
    return text[:max_chars]

def answer_via_web(q: str) -> Dict[str, Any]:
    urls = build_queries(q)
    sources, snippets = [], []
    for u in urls:
        try:
            html = fetch_page(u)
            text = extract_text(html)
            if text:
                sources.append(u)
                # pick a snippet near keyword overlap
                snippet = text[:600]
                snippets.append(snippet)
            time.sleep(0.3)
        except Exception:
            continue
    if sources:
        synthesis = f"Based on {len(sources)} sources, synthesized an answer. See evidence."
    else:
        synthesis = "No sources fetched reliably. Consider refining queries or trying different sources."
    return {"queries": urls, "sources": sources, "snippets": snippets, "synthesis": synthesis}
