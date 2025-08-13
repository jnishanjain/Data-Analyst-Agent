from fastapi import FastAPI, UploadFile, File
from typing import Optional
import pandas as pd
from io import BytesIO
from app.core import process_inputs

app = FastAPI()

@app.post("/")
async def receive_files(
    questions_file: UploadFile = File(..., alias="questions.txt"),
    image_file: Optional[UploadFile] = File(None, alias="image.png"),  # not used yet
    csv_file: Optional[UploadFile] = File(None, alias="data.csv"),
):
    questions_text = (await questions_file.read()).decode("utf-8", errors="ignore")
    df = None
    if csv_file is not None:
        df = pd.read_csv(BytesIO(await csv_file.read()))

    questions, answers, report_md, report_json = process_inputs(questions_text, df)
    return {
        "questions_detected": questions,
        "answers": answers,
        "report_md": report_md,
        "report_json": report_json,
    }
