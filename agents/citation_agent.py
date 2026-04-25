import os
import json
import requests
import re
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Constants
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_API = "https://api.crossref.org/works"
GROQ_API_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

logging.basicConfig(level=logging.INFO)

def extract_references(references):
    """Simple but robust cleaner that focuses on punctuation and spacing."""
    extracted_titles = []
    for ref in references:
        # 1. Basic cleaning: remove [1], flatten newlines/spaces
        clean_ref = re.sub(r'\[\d+\]', '', ref)
        clean_ref = " ".join(clean_ref.split())
        
        # 2. Extract title within quotes
        match = re.search(r"[“\"'']([^”\"'']+)[”\"'']", clean_ref)
        if match:
            title = match.group(1).strip()
        else:
            # Fallback: take the longest part split by common delimiters
            parts = re.split(r'[,.!?]', clean_ref)
            title = max(parts, key=len).strip()

        # 3. ONLY remove trailing commas, dots, or dashes that confuse APIs
        title = re.sub(r'[,\.\-]$', '', title).strip()
        
        # 4. Remove double spaces created by previous cleaning
        title = title.replace("  ", " ")
        
        extracted_titles.append(title[:150])
            
    return extracted_titles
def verify_citation_with_semantic_scholar(title):
    """Query Semantic Scholar for paper existence."""
    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_API,
            params={"query": title, "limit": 1, "fields": "title,abstract,year,externalIds"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("total", 0) > 0:
                return data["data"][0], "verified"
    except Exception as e:
        logging.error(f"Semantic Scholar error: {e}")
    return None, "not_found"

def verify_citations(references):
    """Main loop for citation verification."""
    results = []
    titles = extract_references(references)
    for idx, (ref, title) in enumerate(zip(references, titles)):
        logging.info(f"Checking: {title}")
        paper, status = verify_citation_with_semantic_scholar(title)
        
        results.append({
            "reference_id": idx + 1,
            "raw_reference": ref,
            "extracted_title": title,
            "status": status,
            "matched_paper": paper
        })
        time.sleep(0.5) # Slight delay for API stability
    return results

def analyze_claims_with_groq(claims):
    """Analyze claims and return strictly structured JSON."""
    results = []
    if not GROQ_API_KEY:
        return [{"error": "GROQ_API_KEY missing"}]

    for idx, claim in enumerate(claims):
        try:
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a research integrity assistant. Return ONLY a JSON object with: 'is_accurate' (boolean), 'confidence_score' (float 0-1), and 'short_reason' (string)."
                    },
                    {"role": "user", "content": f"Verify this claim: {claim}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            res = requests.post(GROQ_API_ENDPOINT, 
                                headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, 
                                json=payload)
            if res.status_code == 200:
                analysis = json.loads(res.json()['choices'][0]['message']['content'])
                analysis.update({"claim_id": idx + 1, "claim_text": claim})
                results.append(analysis)
        except Exception as e:
            logging.error(f"Groq error on claim {idx}: {e}")
    return results

def generate_assessment(citations, claims, groq_results):
    """Calculates final score and status."""
    total = len(citations)
    found = len([c for c in citations if c["status"] == "verified"])
    percent = round((found / total * 100), 2) if total > 0 else 0
    
    status = "green" if percent >= 75 else "yellow" if percent >= 40 else "red"
    
    return {
        "overall_status": status,
        "verified_percentage": percent,
        "citation_details": citations,
        "groq_analysis": groq_results
    }