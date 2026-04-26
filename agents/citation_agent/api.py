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

# --- PATH LOGIC ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent 
EXTRACTED_FOLDER = BASE_DIR / "Extraction" / "extracted_results" 

# --- REQUEST MODEL ---
class OrchestratorRequest(BaseModel):
    json_file_name: str
    assessment_mode: str = "comprehensive"

# --- RESPONSE MODELS (Essential for the 'response_model' to work) ---
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

@app.post("/api/v1/assess", response_model=FinalAssessment)
async def analyze_paper(request: OrchestratorRequest):
    try:
        # Handling filename logic
        filename = f"{request.json_file_name}.json"
        file_path = EXTRACTED_FOLDER / filename
        
        logging.info(f"📂 Citation Agent checking: {file_path}")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {filename} not found in {EXTRACTED_FOLDER}")

        with open(file_path, "r") as f:
            paper_data = json.load(f)

        # 1. Process References
        references = paper_data.get("references", [])
        citations_results = verify_citations(references)

        # 2. Extract sections for analysis
        sections_content = [
            paper_data.get('abstract', ''),
            paper_data.get('methodology', ''),
            paper_data.get('results', ''),
            paper_data.get('conclusion', '')
        ]

        # 3. Run Analysis via the logic file
        groq_results = analyze_claims_with_groq(sections_content)
        
        # 4. Generate Final Structure
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