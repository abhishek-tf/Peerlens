import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

# Important: This assumes citation_agent.py is in the same folder
from citation_agent import verify_citations, analyze_claims_with_groq, generate_assessment

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Peerlens Citation Agent")

# --- DYNAMIC PATH LOGIC ---
# 1. Path(__file__) is this current file (api.py)
# 2. .resolve() gets the full absolute path
# 3. .parents[2] goes up 3 levels: citation_agent/ -> agents/ -> Peerlens/
BASE_DIR = Path(__file__).resolve().parents[2]

# Now it points to Peerlens/extracted_results regardless of the computer name
EXTRACTED_FOLDER = BASE_DIR / "Extraction" / "extracted_results"

logging.info(f"📍 Root Directory detected as: {BASE_DIR}")
logging.info(f"📂 Looking for results in: {EXTRACTED_FOLDER}")
# Ensure the folder exists so the agent doesn't crash on startup
EXTRACTED_FOLDER.mkdir(parents=True, exist_ok=True)

# --- REQUEST MODEL ---
class OrchestratorRequest(BaseModel):
    json_file_name: str
    assessment_mode: str = "comprehensive"

# --- RESPONSE MODELS ---
class FlaggedCitation(BaseModel):
    reference_id: int
    raw_reference: str
    ai_cleaned_title: str 
    status: str
    matched_paper: Optional[Dict[str, Any]] = None

class CriticalClaim(BaseModel):
    claim_id: int
    claim_text: str
    is_accurate: bool
    confidence_score: float
    short_reason: str

class FinalAssessment(BaseModel):
    overall_status: str
    summary_message: str
    verified_percentage: float
    total_citations_checked: int 
    flagged_citations: List[FlaggedCitation]
    critical_claims: Union[List[CriticalClaim], str] 

@app.get("/")
def home():
    return {"status": "Citation Agent Online", "port": 8003}

@app.post("/api/v1/citation-report", response_model=FinalAssessment)
async def analyze_paper(request: OrchestratorRequest):
    try:
        # 1. Handling filename logic
        # If the user provides "file.json", we don't want "file.json.json"
        clean_name = request.json_file_name.replace(".json", "")
        filename = f"{clean_name}.json"
        file_path = EXTRACTED_FOLDER / filename
        
        logging.info(f"📂 Citation Agent checking: {file_path}")

        if not file_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"File {filename} not found in {EXTRACTED_FOLDER}. Please check the folder in VS Code."
            )

        # 2. Load the JSON data
        with open(file_path, "r") as f:
            paper_data = json.load(f)

        # 3. Process References
        references = paper_data.get("references", [])
        citations_results = verify_citations(references)

        # 4. Extract sections for analysis
        sections_content = [
            paper_data.get('abstract', ''),
            paper_data.get('methodology', ''),
            paper_data.get('results', ''),
            paper_data.get('conclusion', '')
        ]

        # 5. Run Analysis via the logic file (Groq/AI part)
        groq_results = analyze_claims_with_groq(sections_content)
        
        # 6. Generate Final Structure and return
        return generate_assessment(citations_results, sections_content, groq_results)

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Agent Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Assigned Port: 8003
    uvicorn.run(app, host="0.0.0.0", port=8003)