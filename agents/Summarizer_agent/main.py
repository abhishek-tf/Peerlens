from fastapi import FastAPI
from summariser import summarize_paper
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

@app.post("/summarize")
async def summarize():
    result = summarize_paper()
    model_name = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    return {
        "paper_id": "test-id",
        "summary": result,
        "meta": {
            "model": model_name
        }
    }