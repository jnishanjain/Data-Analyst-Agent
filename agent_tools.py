
import pandas as pd
import json
from bs4 import BeautifulSoup
import re
import requests
from typing import Optional, List, Dict
import tempfile
import os
import mimetypes
from pathlib import Path
import pdfplumber
import docx
import openpyxl
from tavily import TavilyClient
from together import Together
import speech_recognition as sr
from pydub import AudioSegment
import nltk
from nltk.corpus import wordnet as wn
import chess
import chess.engine

from langchain_core.tools import tool

# Download WordNet (once per application)
nltk.download('wordnet')

if not os.path.exists('/usr/games/stockfish'):
    os.system('apt-get update && apt-get install -y stockfish')

DEFAULT_API_URL = "https://agents-course-unit4-scoring.hf.space"

@tool
def add_numbers(a: float, b: float) -> float:
    """
    Adds two numbers and returns the result.

    Args:
        a (float): First number.
        b (float): Second number.

    Returns:
        float: Sum of a and b.
    """
    return a + b

@tool
def subtract_numbers(a: float, b: float) -> float:
    """
    Subtract two number and returns the result.

    Args:
        a (float): Minuend.
        b (float): Subtrahend.

    Returns:
        float: Result of a - b.
    """
    return a - b

@tool
def multiply_numbers(a: float, b: float) -> float:
    """
    Returns the multiplication of two numbers.

    Args:
        a (float): First factor.
        b (float): Second factor.

    Returns:
        float: Product of a and b.
    """
    return a * b

@tool
def divide_numbers(a: float, b: float) -> float:
    """
    Returns the division of two numbers.

    Args:
        a (float): Dividend.
        b (float): Divisor.

    Returns:
        float: Result of a / b.

    Raises:
        ZeroDivisionError: If b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Division by zero is undefined.")
    return a / b

@tool
def modulo_numbers(a: float, b: float) -> float:
    """
    Returns the remainder of dividing two numbers.

    Args:
        a (float): Dividend.
        b (float): Divisor.

    Returns:
        float: Remainder of a divided by b.
    """
    return a % b

@tool
def load_task_text_file_and_extract_text(task_id: str) -> str:
    """
    USE the tool if there is file to load. Loads a file by its task ID and extracts up to 5000 characters of text content.

    Args:
        task_id (str): Unique identifier of the file to load.

    Returns:
        str: Extracted text content from the file (maximum 5000 characters).
             Returns an error message if the file cannot be loaded or is of an unsupported type.
             
    Supported file types: .txt, .csv, .pdf, .docx, .xlsx
    """

    url = f"{DEFAULT_API_URL}/files/{task_id}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return f"File download error: {e}"

    # Detect MIME type and extension
    content_type = response.headers.get("Content-Type", "")
    ext = mimetypes.guess_extension(content_type) or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(response.content)
        tmp_path = Path(tmp.name)
    
    text = None
    try:
        # Handle plain text and CSV files
        if content_type.startswith("text") or tmp_path.suffix in [".txt", ".csv"]:
            with open(tmp_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        # Handle PDF files
        elif tmp_path.suffix == ".pdf" and pdfplumber:
            with pdfplumber.open(tmp_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        # Handle DOCX files
        elif tmp_path.suffix == ".docx" and docx:
            doc = docx.Document(tmp_path)
            text = "\n".join([p.text for p in doc.paragraphs])
        # Handle XLSX files
        elif tmp_path.suffix == ".xlsx" and openpyxl:
            wb = openpyxl.load_workbook(tmp_path)
            text = ""
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    text += "\t".join([str(cell) if cell is not None else "" for cell in row]) + "\n"
        # Fallback: try decoding as UTF-8
        else:
            try:
                text = response.content.decode("utf-8")
            except Exception:
                text = None

        if not text:
            return "Could not extract text from the file."
        # Clean up and limit text length
        text = " ".join(text.split())
        return text[:5000]
    finally:
        # Always remove the temporary file
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@tool
def load_and_describe_image(task_id: str, question: str) -> str:
    """
    USE the tool if there is file to load. Downloads an image by task_id, sends it to a vision-capable LLM along with a user question,
    and returns the model's answer.

    Args:
        task_id (str): The unique identifier of the image file.
        question (str): A natural language question about the image content. Example: "Describe the positions of the chess pieces in the picture."
    Returns:
        str: The answer generated by the vision model based on the image and the question. Returns an error message if the image cannot be processed or the model call fails.

    Supported imgage types: .jpg, .jpeg,.png

    """
    client = Together()
    image_url = f"{DEFAULT_API_URL}/files/{task_id}"
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-Vision-Free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": question}
                    ]
                }
            ]
        )
        answer = response.choices[0].message.content
        return answer
    except Exception as e:
        return f"Error processing image {image_url}: {str(e)}"


@tool
def web_search(query: str, include_domains: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Performs an intelligent web search using the Tavily Search API and returns answer to the user's question. You are an information extraction expert, so extract relevant information from tool's answer.

    Here is few examples how to use tool's answer. 
    Example 1.
                Task: How many planets are there in the Solar System? Use Wikipedia.
                Calling tool: 'web_search' with arguments: {'query': 'How many planets are there in the Solar System', 'include_domains': ['en.wikipedia.org']}
                Tool's answer: There are eight planets in the Solar System: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. This count is based on the International Astronomical Union's definition.
                <think> Okey, eight planets is the answer. I transform it to number 8.<think>
                FINAL ANSWER: 8
    Example 2.
                Task: Who played the Pope in the TV series The Young Pope? Need first name.
                Calling tool: 'web_search' with arguments: {'query': 'Who played the Pope in the TV series The Young Pope'}
                Tool's answer: "The Young Pope is a drama television series created and directed by Paolo Sorrentino. It stars Jude Law as Pope Pius XIII, the first American Pope in history, and Diane Keaton as Sister Mary, his confidante. 
                <think> Okey, Jude Law played Pope. Jude is first name. <think>
                FINAL ANSWER: Jude
                
    
    Description:
        Utilizes the Tavily Search API to retrieve up-to-date and reliable information relevant to answer question. The tool can search for relevant sources in web, analyze them, and generate a final answer.
        Optionally, you can restrict search to specific domains using the include_domains argument.

    Args:
        query (str): The natural language search query based on question. Example: How many planets are there in the solar galaxy
        include_domains (Optional[List[str]]): A list of domains to specifically include in the search results. Example: ["https://en.wikipedia.org"]
    Returns:
    Dictionary with:
        answer(str): Answer based on the search query or an error message if the search fails.
        sources (List[str]): list of relevant URLs
    """
    api_key = os.environ["TVL_API"] 
    tavily = TavilyClient(api_key=api_key)
    result = tavily.search(query, search_depth="advanced", max_results=5, include_answer="basic", include_domains=include_domains)
    
    try:
        #return "You are an information extraction expert. For each question, find and use only the relevant fragment of the text. Check yourself. RESULTS of web search:" +  result["results"][0]["content"]
        return {"answer": result["answer"], "sources": [item.get("url", "") for item in result.get("results", [])]}
    except Exception as e:
        return f"No web search results"
        

@tool
def extract_visible_text_from_url(url: str) -> str:
    """
    Extracts the main visible cleaned text from a webpage URL.
    Args:
        url: The URL of the page to extract text from. Example: "https://en.wikipedia.org/wiki/Artificial_intelligence"
    Returns:
        Cleaned and concatenated main text content from the page (up to 5000 characters), or an error message.
    """
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Удаляем скрипты, стили, навигацию
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()

        paragraphs = [p.get_text(separator=' ', strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]

        # Объединяем и очищаем текст
        text = '\n\n'.join(paragraphs)

        # Убираем лишние пробелы и спецсимволы
        text = re.sub(r'\s+', ' ', text).strip()

        # Ограничиваем длину (2000 символов)
        max_length = 5000
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text
    except Exception as e:
        return f"Error extracting content from URL: {str(e)}"


@tool
def speech_to_text_from_task_audio(task_id: str) -> str:
    """
    USE the tool if there is file to load. Downloads an audio file by task_id (supports .mp3 and .wav), transcribes speech using speech_recognition, and returns the text.

    Args:
        task_id (str): The unique identifier of the audio file.

    Returns:
        str: Transcribed speech from the audio file or an error message.

    Supported formats:
        .mp3, .wav

    Notes:
        - MP3 files are automatically converted to WAV before transcription.
        - Returns an error message if the file cannot be processed.
    """
    url = f"{DEFAULT_API_URL}/files/{task_id}"
    tmp_audio_path = None
    tmp_wav_path = None
    try:
        # Download the audio file
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        # Determine file type (here, by simple extension check; you can improve this by content-type)
        content_type = response.headers.get('Content-Type', '')
        if '.mp3' in url or 'audio/mpeg' in content_type:
            suffix = ".mp3"
        else:
            suffix = ".wav"

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_audio:
            tmp_audio.write(response.content)
            tmp_audio_path = tmp_audio.name

        # If mp3, convert to wav
        if suffix == ".mp3":
            tmp_wav_path = tmp_audio_path.replace('.mp3', '.wav')
            audio = AudioSegment.from_mp3(tmp_audio_path)
            audio.export(tmp_wav_path, format="wav")
            audio_file_path = tmp_wav_path
        else:
            audio_file_path = tmp_audio_path

        # Recognize speech from the audio file
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)  # Default language (English)

        return text
    except Exception as e:
        return f"Error: {e}"
    finally:
        # Remove the temporary files if they were created
        for path in [tmp_audio_path, tmp_wav_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass



@tool
def filter_by_category_wordnet(items: list[str], category: str) -> list[str]:
    """
    Filters a list of strings based on a specified WordNet category.

    Args:
        items: List of elements to filter (e.g., ['cow', 'dog', 'pig']).
        category: WordNet synset name (e.g., 'even-toed_ungulate.n.01' or 'vegetable.n.01').

    Returns:
        Sublist of items that are hyponyms of the specified category.
    """
    try:
        syn = wn.synset(category)
    except nltk.corpus.reader.wordnet.WordNetError:
        return []

    # Recursively collect all hyponyms
    hyponyms = syn.closure(lambda s: s.hyponyms())

    # Set of all lemmas in the category
    valid = {
        lemma.name().replace('_', ' ')
        for s in hyponyms
        for lemma in s.lemmas()
    }

    # Filter the input list
    return [item for item in items if item in valid]


@tool
def chess_analyze(fen: str) -> dict:
    """
    Analyzes a chess position using Stockfish.

    Args:
        fen: FEN string describing the chess position
             (e.g., 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1').

    Returns:
        A dictionary with:
            - 'score': Evaluation in centipawns from White's perspective
                       (positive: advantage White, negative: advantage Black)
            - 'best_move': Best move in UCI format (e.g., 'e2e4')
    """
    # Create a board from the FEN string
    board = chess.Board(fen)

    # Use Stockfish engine (in Hugging Face Spaces, just "stockfish")
    with chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish") as engine:
        # Analyze the position to a reasonable depth
        info = engine.analyse(board, chess.engine.Limit(depth=15))

        # Get the evaluation score (centipawns, from White's point of view)
        score = info["score"].white().score(mate_score=10000)

        # Get the best move in UCI notation
        best_move = info["pv"][0].uci()

    # Return results as a dictionary
    return {"score": score, "best_move": best_move}


@tool
def excel_to_text_by_task_id(
    task_id: str,
    sheet_name: Optional[str] = None
) -> str:
    """
    Loads an Excel file by task ID, extracts the specified worksheet, and returns it as a Markdown table.

    Args:
        task_id: Unique file identifier from the task context.
        sheet_name (optional): Worksheet name or zero-based index as a string (defaults to first sheet).

    Returns:
        Markdown-formatted table as a string, or an error message.
    """
   
    url = f"{DEFAULT_API_URL}/files/{task_id}"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(response.content)
            tmp_path = Path(tmp.name)

        if sheet_name is not None:
            try:
                sheet = int(sheet_name)
            except (ValueError, TypeError):
                sheet = sheet_name
            df = pd.read_excel(tmp_path, sheet_name=sheet)
        else:
            df = pd.read_excel(tmp_path)


        tmp_path.unlink(missing_ok=True)
   
        return df.to_markdown(index=False)

    except Exception as e:
        return f"Error processing Excel file: {str(e)}"
