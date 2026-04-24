import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
 
from models import PaperInput, AssessmentResult
from agent import StreamlinedMethodologyAssessmentAgent
 
# Setup professional logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
# Initialize FastAPI app
app = FastAPI(
    title="Methodology Reproducibility Assessment API",
    description="AI-powered agent to verify methodology reproducibility in research papers.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
 
# CORS middleware for web and cross-agent integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Initialize the Streamlined Agent
logger.info("🚀 Initializing Streamlined Methodology Assessment Agent...")
agent = StreamlinedMethodologyAssessmentAgent()
 
# --- Request Models ---
class AssessmentRequest(BaseModel):
    paper: PaperInput
    pre_extracted_components: Optional[Dict[str, Any]] = None
    assessment_mode: str = "comprehensive"  # "comprehensive" | "quick" | "focused"
 
# --- API Endpoints ---
 
@app.get("/health")
async def health_check():
    """Simple check to verify the agent is alive and responding."""
    return {"status": "online", "agent": "Methodology Reproducibility Checker"}
 
@app.post("/api/v1/assess", response_model=AssessmentResult)
async def run_assessment(request: AssessmentRequest):
    """
    Main endpoint for comprehensive methodology assessment.
    Your teammate's PDF extraction agent will send data here.
    """
    try:
        logger.info(f"📥 Received assessment request for paper: {request.paper.title[:50]}...")
        
        result = await agent.assess(
            paper=request.paper,
            pre_extracted_components=request.pre_extracted_components,
            assessment_mode=request.assessment_mode
        )
        
        logger.info("✅ Assessment completed successfully.")
        return result
        
    except Exception as e:
        logger.error(f"❌ Assessment endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assessment processing failed: {str(e)}")
 
@app.post("/api/v1/quick-assess")
async def run_quick_assessment(paper: PaperInput):
    """
    Faster endpoint for a lightweight methodology check.
    """
    try:
        logger.info(f"📥 Received QUICK assessment request for paper: {paper.title[:50]}...")
        result = await agent.quick_assess(paper)
        return result
    except Exception as e:
        logger.error(f"❌ Quick assessment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
if __name__ == "__main__":
    # Run the server on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
