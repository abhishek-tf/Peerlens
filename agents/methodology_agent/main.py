import logging
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
 
from agent import StreamlinedMethodologyAssessmentAgent, PaperInput, AssessmentResult

 
# Setup professional logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent 
EXTRACTION_RESULTS_DIR = CURRENT_DIR.parent.parent / "Extraction" / "extracted_results"

print(f"\n{'='*60}")
print(f"DEBUG: Agent is looking for JSONs in:\n{EXTRACTION_RESULTS_DIR.absolute()}")
print(f"{'='*60}\n")
 
# Initialize FastAPI app
app = FastAPI(
    title="Methodology Reproducibility Assessment API",
    description="AI-powered agent that pulls data from shared JSON storage.",
    version="2.1.0"
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
logger.info("🚀 Initializing Streamlined Methodology Assessment Agent...")
agent = StreamlinedMethodologyAssessmentAgent()
 
# --- Request Models ---
class AssessmentRequest(BaseModel):
    json_file_name: str 
    pre_extracted_components: Optional[Dict[str, Any]] = None
    assessment_mode: str = "comprehensive" 
 
# --- API Endpoints ---
 
@app.get("/health")
async def health_check():
    return {"status": "online", "agent": "Methodology Reproducibility Checker"}
 
@app.post("/api/v1/assess", response_model=AssessmentResult)
async def run_assessment(request: AssessmentRequest):
    # 1. Locate the file (Logic moved outside try block to avoid catching 404 as 500)
    file_path = EXTRACTION_RESULTS_DIR / f"{request.json_file_name}.json"
    
    if not file_path.exists():
        logger.error(f"📂 File not found at: {file_path}")
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "File Not Found",
                "attempted_path": str(file_path.absolute()),
                "message": f"Make sure '{request.json_file_name}.json' exists in the Extraction results folder."
            }
        )

    try:
        # 2. Load and parse JSON
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"📥 Successfully loaded {request.json_file_name}.json")

        # 3. Map JSON to PaperInput
        paper = PaperInput.from_raw_json(data)
        
        # 4. Run the AI Assessment
        result = await agent.assess(
            paper=paper,
            pre_extracted_components=request.pre_extracted_components,
            assessment_mode=request.assessment_mode
        )
        
        return result
        
    except json.JSONDecodeError:
        logger.error(f"❌ File {request.json_file_name}.json contains invalid JSON.")
        raise HTTPException(status_code=400, detail="The targeted file is not a valid JSON.")
    except HTTPException as http_exc:
        # Re-raise FastAPIs own HTTP exceptions
        raise http_exc
    except Exception as e:
        logger.error(f"❌ Assessment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Agent Error: {str(e)}")
 
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)