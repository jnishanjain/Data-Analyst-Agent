import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO

def scrape_website(url: str) -> str:
    """
    Scrape main readable content + tables from a Wikipedia article.
    Returns combined plain text and table CSV snippets.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/0.1)"}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        return f"Failed to fetch {url}: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    # ✅ Wikipedia: main article text lives in <div id="mw-content-text">
    content_div = soup.find("div", {"id": "mw-content-text"})
    if not content_div:
        return "No content section found."

    texts = []
    for p in content_div.find_all(["p", "h1", "h2", "h3"], recursive=True):
        text = p.get_text(strip=True)
        if text:
            texts.append(text)

    # ✅ Get first few tables (like the “highest-grossing films” table)
    tables = []
    for table in content_div.find_all("table", {"class": "wikitable"}):
        try:
            df = pd.read_html(StringIO(str(table)))[0]
            tables.append(df.head(10).to_csv(index=False))  # limit size
        except Exception:
            continue

    combined = "\n\n".join(texts + tables)
    return combined
