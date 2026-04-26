import os
import json
import requests
import re
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# --- PATH CORRECTION FOR SUB-FOLDER ---
# Since this file is now in agents/citation_agent/, we go up 3 levels to reach root
BASE_DIR = Path(__file__).resolve().parent.parent.parent 
# Load .env from the current folder (agents/citation_agent/.env)
load_dotenv(Path(__file__).resolve().parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Constants
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_API = "https://api.crossref.org/works"
GROQ_API_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

logging.basicConfig(level=logging.INFO)

def clean_title_with_groq(raw_ref):
    """Uses AI to fix smashed words and extract a clean title for better API matching."""
    if not GROQ_API_KEY:
        logging.warning("⚠️ No Groq API Key found. Skipping AI cleaning.")
        return raw_ref
    try:
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a research assistant. Extract ONLY the paper title from the text. Fix missing spaces. Return ONLY the title string."
                },
                {"role": "user", "content": raw_ref}
            ],
            "temperature": 0
        }
        res = requests.post(GROQ_API_ENDPOINT, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=payload)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'].strip().strip('"')
    except Exception as e:
        logging.error(f"Groq cleaning error: {e}")
    return raw_ref

def verify_citation_multi_source(title):
    """Checks Semantic Scholar first, then fallbacks to Crossref."""
    try:
        ss_response = requests.get(
            SEMANTIC_SCHOLAR_API,
            params={"query": title, "limit": 1, "fields": "title,year,authors,url"},
            timeout=10
        )
        if ss_response.status_code == 200:
            data = ss_response.json()
            if data.get("total", 0) > 0:
                logging.info(f"✅ Found on Semantic Scholar: {title[:50]}...")
                return data["data"][0], "verified"
    except Exception as e:
        logging.error(f"Semantic Scholar error: {e}")

    logging.info(f"🔍 Falling back to Crossref for: {title[:50]}...")
    try:
        cr_response = requests.get(
            CROSSREF_API,
            params={"query.bibliographic": title, "rows": 1},
            timeout=10
        )
        if cr_response.status_code == 200:
            items = cr_response.json().get("message", {}).get("items", [])
            if items:
                paper = items[0]
                normalized = {
                    "title": paper.get("title", ["Unknown"])[0],
                    "year": paper.get("published", {}).get("date-parts", [[None]])[0][0],
                    "url": paper.get("URL", "")
                }
                logging.info(f"✅ Found on Crossref: {normalized['title'][:50]}...")
                return normalized, "verified"
    except Exception as e:
        logging.error(f"Crossref error: {e}")

    return None, "not_found"

def verify_citations(references):
    """Main loop: AI cleans the title, then checks multiple sources."""
    if not references:
        return []
        
    results = []
    for idx, ref in enumerate(references):
        logging.info(f"Processing reference {idx+1}...")
        clean_title = clean_title_with_groq(ref)
        paper, status = verify_citation_multi_source(clean_title)
        
        results.append({
            "reference_id": idx + 1,
            "raw_reference": ref,
            "ai_cleaned_title": clean_title,
            "status": status,
            "matched_paper": paper
        })
        time.sleep(0.5) 
    return results

def analyze_claims_with_groq(sections_content):
    """Analyze methodology/results logic using Groq."""
    results = []
    active_claims = [c for c in sections_content if c and len(c.strip()) > 10]
    
    for idx, claim in enumerate(active_claims):
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
            res = requests.post(GROQ_API_ENDPOINT, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=payload)
            if res.status_code == 200:
                analysis = json.loads(res.json()['choices'][0]['message']['content'])
                analysis.update({"claim_id": idx + 1, "claim_text": claim[:150] + "..."})
                results.append(analysis)
        except Exception as e:
            logging.error(f"Groq logic error: {e}")
    return results

def generate_assessment(citations, sections_content, groq_results):
    """Compiles the final risk report."""
    total = len(citations)
    bad_citations = [c for c in citations if c["status"] != "verified"]
    found_count = total - len(bad_citations)
    
    percent = round((found_count / total * 100), 2) if total > 0 else 0
    status = "green" if percent >= 75 else "yellow" if percent >= 40 else "red"
    
    critical_claims = [r for r in groq_results if r.get("is_accurate") is False]

    return {
        "overall_status": status,
        "summary_message": f"Analyzed {total} citations. {len(bad_citations)} flags found.",
        "verified_percentage": percent,
        "total_citations_checked": total,
        "flagged_citations": bad_citations,
        "critical_claims": critical_claims if critical_claims else "No logical inaccuracies found"
    }

if __name__ == "__main__":
    # --- ✅ UPDATED FOR AUTOMATIC LOCAL TESTING ---
    EXTRACTED_FOLDER = BASE_DIR / "extracted_results"
    
    # This looks for the first JSON file it can find in the folder to test with
    json_files = list(EXTRACTED_FOLDER.glob("*.json"))
    
    if json_files:
        input_file = json_files[0]
        logging.info(f"🚀 Testing logic on: {input_file.name}")
        with open(input_file, 'r') as f:
            paper_data = json.load(f)
            
        citations = verify_citations(paper_data.get('references', []))
        sections = [
            paper_data.get('abstract', ''),
            paper_data.get('methodology', ''),
            paper_data.get('results', ''),
            paper_data.get('conclusion', '')
        ]
        groq_results = analyze_claims_with_groq(sections)
        
        report = generate_assessment(citations, sections, groq_results)
        
        output_path = BASE_DIR / "results" / "final_report.json"
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as out:
            json.dump(report, out, indent=2)
        logging.info(f"✅ Success! Report saved at {output_path}")
    else:
        logging.error(f"❌ No JSON files found in {EXTRACTED_FOLDER}")