from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from summariser import summarize_paper
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Path to extracted JSON folder
BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXTRACTED_FOLDER = BASE_DIR / "Extraction" / "extracted_results"


# ✅ REQUEST MODEL (Fixes Swagger UI empty body issue)
class SummarizeRequest(BaseModel):
    json_file_name: str
    assessment_mode: str = "comprehensive"


@app.post("/api/v1/summarize")
async def summarize(payload: SummarizeRequest):
    try:
        json_file_name = payload.json_file_name
        file_path = EXTRACTED_FOLDER / f"{json_file_name}.json"
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"JSON file not found: {file_path}"
            )
        with open(file_path, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
        sections = extracted_data.get("sections", {})
        data = {
            "title": extracted_data.get("title", ""),
            "abstract": sections.get("ABSTRACT", ""),
            "methodology": sections.get("METHODOLOGY", "") or sections.get("METHODS", ""),
            "results": sections.get("RESULTS", ""),
            "conclusion": sections.get("CONCLUSION", "")
        }
        result = summarize_paper(data)
        return {
            "paper_id": json_file_name,
            "summary": result.get("summary", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


