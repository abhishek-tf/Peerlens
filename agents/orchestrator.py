import asyncio
import httpx
import logging
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Orchestrator")

app = FastAPI(title="Peerlens Master Orchestrator")

# CORS so your Next.js app can talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Service Registry ---
EXTRACTION_SERVICE_URL = "http://localhost:8000/extract" 
METHODOLOGY_AGENT_URL = "http://localhost:8001/api/v1/assess"
# CITAION_AGENT_URL = "http://localhost:8002/api/v1/assess"
SUMMARY_AGENT_URL = "http://localhost:8002/api/v1/summarize"

@app.post("/api/v1/full-review")
async def process_research_paper(file: UploadFile = File(...)):
    """
    1. Sends PDF to Extraction Service
    2. Receives file_id (JSON name)
    3. Triggers all Agents in parallel
    4. Aggregates results for the Frontend
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # --- PHASE 1: EXTRACTION ---
            logger.info(f"📤 Sending {file.filename} to Extraction Service...")
            
            # Forward the file to the extraction API
            file_content = await file.read()
            files = {"file": (file.filename, file_content, file.content_type)}
            
            extract_resp = await client.post(EXTRACTION_SERVICE_URL, files=files)
            
            if extract_resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Extraction failed.")

            # Your extraction team member's code saves the file. 
            # We need to know what filename they used.
            # Assuming the API returns the filename without extension:
            file_id = os.path.splitext(file.filename)[0]
            logger.info(f"✅ Extraction complete. JSON created: {file_id}.json")

            # --- PHASE 2: AGENT ORCHESTRATION ---
            logger.info(f"🤖 Triggering agents for {file_id}...")
            
            # Payload for the 'Pull-based' agents we updated in Step 1
            agent_payload = {
                "json_file_name": file_id,
                "assessment_mode": "comprehensive"
            }

            # Define the tasks to run in parallel
            tasks = [
                client.post(METHODOLOGY_AGENT_URL, json=agent_payload),
                # Add Citation and Summary tasks here as they become ready:
                # client.post(CITATION_AGENT_URL, json=agent_payload),
                client.post(SUMMARY_AGENT_URL, json=agent_payload),
            ]

            # Fire all requests simultaneously
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # --- PHASE 3: AGGREGATION ---
            # We process responses and handle potential agent crashes gracefully
            results = {
                "file_id": file_id,
                "status": "completed",
                "reports": {}
            }

            # Map the responses back to their respective agents
            agent_names = ["methodology", "summarizer"] # Add "citation" later
            
            for name, resp in zip(agent_names, responses):
                if isinstance(resp, Exception):
                    results["reports"][name] = {"error": f"Agent unreachable: {str(resp)}"}
                elif resp.status_code != 200:
                    results["reports"][name] = {"error": f"Agent error: {resp.text}"}
                else:
                    results["reports"][name] = resp.json()

            return results

        except Exception as e:
            logger.error(f"❌ Orchestration Error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)