'''
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from openai import OpenAI
import re, json, io, base64, logging
import pandas as pd
import matplotlib.pyplot as plt
from app.llm import LLMClient
from app.web import scrape_website

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI()
app = FastAPI()
llm = LLMClient()

# --- helper: extract first URL from text ---
def extract_url(text: str) -> str | None:
    match = re.search(r'(https?://\S+)', text)
    return match.group(1) if match else None

# --- helper: plot and encode base64 ---
def plot_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

# --- helper: find column ignoring case ---
def find_col(df: pd.DataFrame, options):
    for col in df.columns:
        if col.lower() in [o.lower() for o in options]:
            return col
    return None

@app.post("/")
async def answer_questions(
    questions_txt: UploadFile = File(...),
    data: UploadFile = File(None)  # optional CSV
):
    # Read uploaded file (questions)
    content_bytes = await questions_txt.read()
    content = content_bytes.decode("utf-8").splitlines()

    # First line should be URL
    url = None
    if content[0].lower().startswith("url:"):
        url = content[0].split(":", 1)[1].strip()
        questions = "\n".join(content[1:])
    else:
        url = extract_url("\n".join(content))
        questions = "\n".join(content)

    # Scrape if URL present
    context = scrape_website(url) if url else ""

    # --- Handle CSV if uploaded ---
    if data:
        try:
            logger.info("CSV file detected, starting analysis...")
            file_bytes = await data.read()
            df = pd.read_csv(io.StringIO(file_bytes.decode("utf-8")))
            logger.info(f"CSV loaded with columns: {list(df.columns)}")

            # Find relevant columns
            sales_col = find_col(df, ["sales", "amount", "revenue", "value"])
            region_col = find_col(df, ["region", "area", "location"])
            date_col = find_col(df, ["date", "day", "order_date"])

            if not sales_col:
                logger.error("No sales-like column found.")
                return JSONResponse(content={"error": "No sales column found."})

            # Convert data
            df[sales_col] = pd.to_numeric(df[sales_col], errors="coerce")
            df = df.dropna(subset=[sales_col])

            # Total sales
            total_sales = df[sales_col].sum()

            # Top region
            top_region = ""
            if region_col:
                top_region = df.groupby(region_col)[sales_col].sum().idxmax()

            # Day-sales correlation
            day_sales_corr = 0
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                df = df.dropna(subset=[date_col])
                df["day"] = df[date_col].dt.day
                if df["day"].nunique() > 1:
                    day_sales_corr = df["day"].corr(df[sales_col])

            # Median sales
            median_sales = df[sales_col].median()

            # Total sales tax (10%)
            total_sales_tax = total_sales * 0.1

            # Bar chart by region
            bar_chart_b64 = ""
            if region_col:
                fig, ax = plt.subplots()
                df.groupby(region_col)[sales_col].sum().plot(kind="bar", color="blue", ax=ax)
                ax.set_ylabel("Sales")
                ax.set_title("Sales by Region")
                bar_chart_b64 = plot_to_base64(fig)

            # Cumulative sales chart
            cumulative_chart_b64 = ""
            if date_col:
                df_sorted = df.sort_values(date_col)
                df_sorted["Cumulative"] = df_sorted[sales_col].cumsum()
                fig, ax = plt.subplots()
                ax.plot(df_sorted[date_col], df_sorted["Cumulative"], color="red")
                ax.set_ylabel("Cumulative Sales")
                ax.set_title("Cumulative Sales Over Time")
                cumulative_chart_b64 = plot_to_base64(fig)

            result = {
                "total_sales": float(total_sales),
                "top_region": str(top_region),
                "day_sales_correlation": float(day_sales_corr) if day_sales_corr else 0,
                "bar_chart": bar_chart_b64,
                "median_sales": float(median_sales),
                "total_sales_tax": float(total_sales_tax),
                "cumulative_sales_chart": cumulative_chart_b64,
            }

            logger.info(f"Analysis complete. Result: {result}")
            return JSONResponse(content=result)

        except Exception as e:
            logger.exception("Error processing CSV")
            return JSONResponse(content={"error": str(e)})

    # --- Else fallback to LLM if no CSV ---
    prompt = f"""
    Use the following scraped context from {url or "N/A"} to answer the questions.

    Context:
    {context[:4000]}

    Questions:
    {questions}

    Return answers as a JSON list.
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    raw_text = response.output[0].content[0].text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = [raw_text]

    return JSONResponse(content=parsed)
'''
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from openai import OpenAI
import re, json, io
import pandas as pd

client = OpenAI()
app = FastAPI()

# --- helper: extract first URL from text ---
def extract_url(text: str) -> str | None:
    match = re.search(r'(https?://\S+)', text)
    return match.group(1) if match else None


@app.post("/")
async def answer_questions(
    questions_txt: UploadFile = File(...),
    data: UploadFile = File(None)  # optional CSV
):
    # Read uploaded questions
    content_bytes = await questions_txt.read()
    questions = content_bytes.decode("utf-8").strip()

    # Detect URL in the question file (optional)
    url = None
    if questions.lower().startswith("url:"):
        first_line, *rest = questions.splitlines()
        url = first_line.split(":", 1)[1].strip()
        questions = "\n".join(rest)
    else:
        url = extract_url(questions)

    # --- If CSV provided, summarize it ---
    dataset_summary = ""
    if data:
        file_bytes = await data.read()
        df = pd.read_csv(io.StringIO(file_bytes.decode("utf-8")))

        # Summarize dataset (columns, dtypes, sample, stats)
        dataset_summary = f"""
        Columns: {list(df.columns)}
        Data types: {df.dtypes.to_dict()}
        Head:
        {df.head(5).to_string(index=False)}
        Summary stats:
        {df.describe(include="all").to_string()}
        """

    # --- Build prompt for LLM ---
    prompt = f"""
    You are a data analyst. 
    Context: Here is the dataset summary and metadata.
    Dataset summary:
    {dataset_summary}

    Questions:
    {questions}

    Instructions:
    - Answer the questions ONLY using the dataset summary above.
    - Return your answers in the SAME order as the questions.
    - Format the final output strictly as a valid JSON array: [a1, a2, a3, ...]
    - Do not include explanations, keys, or text outside the array.
    """

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from openai import OpenAI
import re, json, io
import pandas as pd

client = OpenAI()
app = FastAPI()

# --- helper: extract first URL from text ---
def extract_url(text: str) -> str | None:
    match = re.search(r'(https?://\S+)', text)
    return match.group(1) if match else None


@app.post("/")
async def answer_questions(
    questions_txt: UploadFile = File(...),
    data: UploadFile = File(None)  # optional CSV
):
    # Read uploaded questions
    content_bytes = await questions_txt.read()
    questions = content_bytes.decode("utf-8").strip()

    # Detect URL in the question file (optional)
    url = None
    if questions.lower().startswith("url:"):
        first_line, *rest = questions.splitlines()
        url = first_line.split(":", 1)[1].strip()
        questions = "\n".join(rest)
    else:
        url = extract_url(questions)

    # --- If CSV provided, summarize it ---
    dataset_summary = ""
    if data:
        file_bytes = await data.read()
        df = pd.read_csv(io.StringIO(file_bytes.decode("utf-8")))

        # Summarize dataset (columns, dtypes, sample, stats)
        dataset_summary = f"""
        Columns: {list(df.columns)}
        Data types: {df.dtypes.to_dict()}
        Head:
        {df.head(5).to_string(index=False)}
        Summary stats:
        {df.describe(include="all").to_string()}
        """

    # --- Build prompt for LLM ---
    prompt = f"""
    You are a data analyst. 
    Context: Here is the dataset summary and metadata.
    Dataset summary:
    {dataset_summary}

    Questions:
    {questions}

    Instructions:
    - Answer the questions ONLY using the dataset summary above.
    - Return your answers in the SAME order as the questions.
    - Format the final output strictly as a valid JSON array: [a1, a2, a3, ...]
    - Do not include explanations, keys, or text outside the array.
    """
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from openai import OpenAI
import re, json, io
import pandas as pd

client = OpenAI()
app = FastAPI()

# --- helper: extract first URL from text ---
def extract_url(text: str) -> str | None:
    match = re.search(r'(https?://\S+)', text)

    return match.group(1) if match else None


@app.post("/")
async def answer_questions(
    questions_txt: UploadFile = File(...),
    data: UploadFile = File(None)  # optional CSV
):
    # Read uploaded questions
    content_bytes = await questions_txt.read()
    questions = content_bytes.decode("utf-8").strip()

    # Detect URL in the question file (optional)
    url = None
    if questions.lower().startswith("url:"):
        first_line, *rest = questions.splitlines()
        url = first_line.split(":", 1)[1].strip()
        questions = "\n".join(rest)
    else:
        url = extract_url(questions)

    # --- If CSV provided, summarize it ---
    dataset_summary = ""
    if data:
        file_bytes = await data.read()
        df = pd.read_csv(io.StringIO(file_bytes.decode("utf-8")))

        # Summarize dataset (columns, dtypes, sample, stats)
        dataset_summary = f"""
        Columns: {list(df.columns)}
        Data types: {df.dtypes.to_dict()}
        Head:
        {df.head(5).to_string(index=False)}
        Summary stats:
        {df.describe(include="all").to_string()}
        """

    # --- Build prompt for LLM ---
    prompt = f"""
    You are a data analyst. 
    Context: Here is the dataset summary and metadata.
    Dataset summary:
    {dataset_summary}

    Questions:
    {questions}

    Instructions:
    - Answer the questions ONLY using the dataset summary above.
    - Return your answers in the SAME order as the questions.
    - Format the final output strictly as a valid JSON array: [a1, a2, a3, ...]
    - Do not include explanations, keys, or text outside the array.
    """

    # Call LLM
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    raw_text = response.output[0].content[0].text.strip()

    # Clean markdown code fences if any
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text

    # Parse JSON safely
    try:
        parsed = json.loads(raw_text)
        if not isinstance(parsed, list):
            parsed = [parsed]
    except json.JSONDecodeError:
        parsed = [raw_text]

    return JSONResponse(content=parsed)
