import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
# Import your logic functions from your script
from citation_agent import verify_citations, analyze_claims_with_groq, generate_assessment

app = FastAPI()

# 1. Define what the incoming Research Paper JSON looks like
class ResearchPaper(BaseModel):
    title: str
    abstract: Optional[str] = ""
    results: Optional[str] = ""
    conclusion: Optional[str] = ""
    references: List[str]

@app.get("/")
def read_root():
    return {"message": "Citation Agent API is online and ready for JSON data"}

@app.post("/citation-agent/analyze")
async def analyze_paper(paper: ResearchPaper):
    """
    This endpoint receives JSON data directly from your teammate's service.
    """
    try:
        # 1. Run Verification
        # Accessing paper.references from the JSON body
        citations = verify_citations(paper.references)

        # 2. Prepare claims for Llama (Groq)
        claims = [
            f"Abstract: {paper.abstract}",
            f"Results: {paper.results}",
            f"Conclusion: {paper.conclusion}"
        ]
        # Filter out empty sections
        claims = [c for c in claims if len(c) > 10]

        # 3. Run Llama Analysis
        groq_results = analyze_claims_with_groq(claims)

        # 4. Create the final response
        final_assessment = generate_assessment(citations, claims, groq_results)

        # Return the JSON directly to your teammate
        return final_assessment

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

# Keep this if you still want to serve the last saved file
@app.get("/citation-agent/last-results")
def get_last_results():
    results_path = Path("./results/output.json")
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="No previous results found")
    with open(results_path, "r") as f:
        return json.load(f)