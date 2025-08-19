# Data Analyst Agent

A FastAPI service that analyzes CSV datasets using natural-language instructions. It executes multi-step analysis plans (filtering, grouping, aggregation, visualization) and returns structured results and optional plots. Designed for lightweight deployment with Uvicorn and cloud platforms like Render.

## Features

- Natural-language to analysis pipeline (plan execution)
- CSV ingestion and safe file handling
- Filtering, grouping, aggregation on tabular data
- Optional plotting via Matplotlib
- FastAPI endpoints for programmatic access
- Uvicorn server for simple deployment

## Project Structure

app/
init.py # Package init; wires core interfaces
api.py # FastAPI app with routes for health and analysis
core.py # Request parsing, validation, and plan orchestration
csv_ops.py # CSV operations: load, filter, groupby, aggregate, plot
io.py # For loading files
llm.py # Communicating with the LLM
main.py  
qna.py
report.py
web.py

requirements.txt # Runtime dependencies
README.md # This file
> Paths may differ slightly; adjust to your repository layout.

## API Overview

Base URL: http://host:PORT

- GET `/health`  
  Returns service health status.

- POST `/analyze`  
  Accepts a CSV and a natural-language instruction string; returns results and optional plot.

### Request (multipart/form-data)

- `file`: CSV file to analyze
- `instruction`: e.g., “Group by region and compute average sales; plot bar chart.”

### Response (application/json)

- `status`: `"ok"` | `"error"`
- `steps`: parsed/derived analysis plan
- `result`: tabular result (rows/columns) when applicable
- `plot_url`: URL/relative path if a plot is generated
- `message`: error or info

### Example (curl)

curl -X POST http://localhost:8000/analyze
-F "file=@/path/to/data.csv"


## How It Works

1. Instruction parsing converts text to an executable plan (load → filter → groupby → aggregate → plot).
2. CSV operations use Pandas-like transformations implemented in `csv_ops.py`.
3. Optional plotting generates figures via Matplotlib and saves them to a static location.
4. The API returns structured data and references to any generated assets.

## Local Development

Prerequisites:
- Python 3.11+ recommended
- pip

Setup:

python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

Run:

uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload


## Deployment (Render)

- Create a new Web Service pointing to your repository.
- Start command:

uvicorn app.api:app --host 0.0.0.0 --port ${PORT}

- Ensure all runtime dependencies are listed in `requirements.txt`.
- Pin a Python version supported by your dependencies (recommended 3.11).
  - Example environment var: `PYTHON_VERSION=3.11.9`.

If using plots, include Matplotlib and a compatible NumPy in `requirements.txt`:

numpy==1.26.4
matplotlib==3.8.4

If deployment fails due to missing deps, clear the build cache and redeploy.

## Configuration

Environment variables (optional):
- `PORT`: port for Uvicorn (Render supplies this)
- `LOG_LEVEL`: `info` or `debug`
- `MAX_FILE_SIZE_MB`: limit uploads
- `STORAGE_DIR`: where to save plots/temp files

Uvicorn example:

uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000} --log-level ${LOG_LEVEL:-info}


## Usage Examples

Instruction-only analysis (no plots):
- “Filter rows where year >= 2022 and country == 'IN', then compute mean of price.”

Aggregations:
- “Group by category, aggregate sum revenue and avg quantity.”

Plotting:
- “Group by region and plot total sales as a bar chart.”

CSV requirements:
- Header row present
- Consistent column types for aggregations
- Reasonable file size (configurable)

## Error Handling

- Unsupported instruction: returns `status=error` with guidance.
- Missing columns: returns error with missing field names.
- CSV parse errors: returns error and hint to check delimiter/encoding.
- Plotting unavailable: returns error suggesting to install Matplotlib in production.

## Extending

- Add operations: Implement a new function in `csv_ops.py` and map it in `core.py`’s planner.
- Add new plot types: Implement `plot_*` functions and expose them via instruction parsing.
- Validation: Introduce Pydantic models in `api.py` for stronger typing and error messages.
- Auth: Add API key middleware or FastAPI dependencies.

## Testing

- Unit tests for `csv_ops`:
  - Load CSV, run filter/group/agg, verify outputs.
- Endpoint tests:
  - Use FastAPI’s `TestClient` to test `/analyze` with sample CSV uploads.

## Performance Notes

- Prefer vectorized operations.
- Avoid loading huge CSVs into memory; consider chunking for large files.
- Defer heavy imports (like Matplotlib) inside functions that need them.

## Security

- Validate file type (CSV) and size.
- Sanitize filenames and write to a controlled `STORAGE_DIR`.
- Never execute user-provided code; only parse a constrained instruction grammar.

## License

MIT.

## Acknowledgements

Built with FastAPI and Uvicorn. Plotting powered by Matplotlib 
