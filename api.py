from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Optional
import pandas as pd
from io import BytesIO

from app.core import process_inputs

app = FastAPI()

@app.post("/")
async def receive_files(
    questions_file: UploadFile = File(..., alias="questions.txt"),
    image_file: Optional[UploadFile] = File(None, alias="image.png"),
    csv_file: Optional[UploadFile] = File(None, alias="data.csv"),
):
    if questions_file.content_type not in ("text/plain", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="questions.txt must be text/plain")

    questions_text = (await questions_file.read()).decode("utf-8", errors="ignore")

    df = None
    if csv_file is not None:
        csv_bytes = await csv_file.read()
        try:
            df = pd.read_csv(BytesIO(csv_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    questions, answers, report_md, report_json = process_inputs(questions_text, df)
    return {
        "questions_detected": questions,
        "answers": answers,
        "report_md": report_md,
        "report_json": report_json,
    }
