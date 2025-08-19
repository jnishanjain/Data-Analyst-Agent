import argparse
import json
from app.io import load_txt, load_csv_optional
from app.core import process_inputs

def run(txt_path, csv_path=None):
    text = load_txt(txt_path)
    df = load_csv_optional(csv_path)
    questions, answers, report_md, report_json = process_inputs(text, df)

    # ✅ Extract *only* the plain answers
    answers_only = [a.get("answer", "") for a in answers]

    # Print only the JSON array
    print(json.dumps(answers_only, ensure_ascii=False, indent=2))

    # Persist the same JSON array
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(answers_only, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--txt", required=True)
    parser.add_argument("--csv")
    args = parser.parse_args()
    run(args.txt, args.csv)
