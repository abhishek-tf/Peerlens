import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
from citation_agent import verify_citations, analyze_claims_with_groq, generate_assessment

app = FastAPI()

# Configuration: Path where Abhinav saves his JSON files
EXTRACTED_FOLDER = Path("./extracted")

# Response Models for documentation
class CitationDetail(BaseModel):
    reference_id: int
    raw_reference: str
    extracted_title: str
    status: str
    matched_paper: Optional[Dict[str, Any]] = None

class ClaimAnalysis(BaseModel):
    claim_id: int
    claim_text: str
    is_accurate: bool
    confidence_score: float
    short_reason: str

class FinalAssessment(BaseModel):
    overall_status: str
    verified_percentage: float
    citation_details: List[CitationDetail]
    groq_analysis: List[ClaimAnalysis]

@app.get("/")
def home():
    return {"status": "Citation Agent Online", "folder_watched": str(EXTRACTED_FOLDER.absolute())}

@app.post("/citation-agent/analyze/{paper_name}", response_model=FinalAssessment)
async def analyze_paper_by_name(paper_name: str):
    """
    Abhishek/Abhinav trigger this. 
    It reads {paper_name}.json from the /extracted folder.
    """
    try:
        # Support both 'papername' and 'papername.json'
        filename = paper_name if paper_name.endswith(".json") else f"{paper_name}.json"
        file_path = EXTRACTED_FOLDER / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {filename} not found in extracted folder.")

        with open(file_path, "r") as f:
            paper_data = json.load(f)

        # 1. Process References
        references = paper_data.get("references", [])
        citations_results = verify_citations(references)

        # 2. Extract sections for AI validation
        # We use .get to prevent crashing if a section is missing
        claims_to_check = []
        for section in ["abstract", "methodology", "results", "conclusion"]:
            content = paper_data.get(section, "")
            if content and len(content) > 20:
                claims_to_check.append(f"{section.capitalize()}: {content[:1000]}") # Send a good snippet

        # 3. AI Claim Analysis
        groq_results = analyze_claims_with_groq(claims_to_check)

        # 4. Compile Final Report
        return generate_assessment(citations_results, claims_to_check, groq_results)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Agent Processing Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)