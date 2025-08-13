import argparse
import json
from app.io import load_txt, load_csv_optional
from app.core import process_inputs

def run(txt_path, csv_path=None):
    text = load_txt(txt_path)
    df = load_csv_optional(csv_path)
    questions, answers, report_md, report_json = process_inputs(text, df)
    """print(report_md)
    with open("report.json", "w", encoding="utf-8") as f:
        f.write(report_json)
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(report_md)
"""
   

# Just take out the answers from the answers list
    answers_only = [a.get("answer", "") for a in answers]

    with open("report.json", "w", encoding="utf-8") as f:   
        json.dump({answers_only}, f, ensure_ascii=False, indent=2)

# Optional: also print to console
    print(json.dumps({answers_only}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--txt", required=True)
    parser.add_argument("--csv")
    args = parser.parse_args()
    run(args.txt, args.csv)
