import argparse
from app.io import load_txt, load_csv_optional
from app.core import process_inputs 

def run(txt_path, csv_path=None):
    text = load_txt(txt_path)
    df = load_csv_optional(csv_path)
    questions, answers, report_md, report_json = process_inputs(text, df)
    print(report_md)
    with open("report.json", "w", encoding="utf-8") as f:
        f.write(report_json)
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(report_md)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--txt", required=True)
    parser.add_argument("--csv", required=False)
    args = parser.parse_args()
    run(args.txt, args.csv)
