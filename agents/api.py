import json
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from citation_agent import verify_citations, analyze_claims_with_groq, generate_assessment

# Set up logging so we can see errors in the terminal
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Peerlens Analysis API")

# --- PATH LOGIC UPDATED FOR ABHINAV'S FOLDER ---
BASE_DIR = Path(__file__).resolve().parent.parent
# ✅ FIXED: Changed "extraction" to "Extraction" to match your actual folder name
EXTRACTED_FOLDER = BASE_DIR / "Extraction" 

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
    return {
        "status": "AI Citation Agent Online", 
        "mode": "Double-AI (Clean + Multi-Source)",
        "folder_watched": str(EXTRACTED_FOLDER.absolute())
    }

@app.post("/citation-agent/analyze/{paper_name}", response_model=FinalAssessment)
async def analyze_paper_by_name(paper_name: str):
    try:
        filename = paper_name if paper_name.endswith(".json") else f"{paper_name}.json"
        file_path = EXTRACTED_FOLDER / filename
        
        logging.info(f"📂 API looking for file at: {file_path}")

        if not file_path.exists():
            # Raise this specifically so it doesn't get caught by the general Exception block
            raise HTTPException(status_code=404, detail=f"File {filename} not found at {file_path}")

        with open(file_path, "r") as f:
            paper_data = json.load(f)

        # 1. Process References
        references = paper_data.get("references", [])
        citations_results = verify_citations(references)

        # 2. Extract sections for AI validation
        sections_content = [
            paper_data.get('abstract', ''),
            paper_data.get('methodology', ''),
            paper_data.get('results', ''),
            paper_data.get('conclusion', '')
        ]

        # 3. AI Claim Analysis
        groq_results = analyze_claims_with_groq(sections_content)

        # 4. Compile Final Report
        report = generate_assessment(citations_results, sections_content, groq_results)
        
        return report

    except HTTPException as he:
        # Re-raise HTTP exceptions so Swagger shows 404 correctly
        raise he
    except Exception as e:
        import traceback
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Agent Processing Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)