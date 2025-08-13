import requests
from bs4 import BeautifulSoup

def build_queries(question: str):
    return ["https://en.wikipedia.org/wiki/Main_Page"]

def fetch_page(url: str):
    r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def extract_text(html: str, max_chars=2000):
    soup = BeautifulSoup(html, "html.parser")
    ps = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    return " ".join(ps)[:max_chars]

def answer_via_web(q: str):
    urls = build_queries(q)
    sources, snippets = [], []
    for url in urls:
        try:
            text = extract_text(fetch_page(url))
            if text:
                sources.append(url)
                snippets.append(text[:500])
        except:
            continue
    return {
        "queries": urls,
        "sources": sources,
        "snippets": snippets,
        "synthesis": f"Synthesized from {len(sources)} sources." if sources else "No sources fetched."
    }
