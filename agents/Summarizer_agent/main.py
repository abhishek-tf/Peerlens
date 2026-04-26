from fastapi import FastAPI, UploadFile, File, HTTPException
from summariser import summarize_paper
import requests
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

EXTRACT_API_URL = "http://127.0.0.1:8000/extract"


@app.post("/summarize")
async def summarize(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        response = requests.post(
            EXTRACT_API_URL,
            files={"file": (file.filename, file_bytes, "application/pdf")}
        )
        if response.status_code != 200:
            raise HTTPException(500, "Extraction API failed")
        extracted_data = response.json()
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
            "paper_id": str(uuid.uuid4()),   # ✅ FIXED HERE
            "summary": result.get("summary", "")
        }
    except Exception as e:
        raise HTTPException(500, str(e))
