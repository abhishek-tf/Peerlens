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

# Configure logging
logging.basicConfig(level=logging.INFO)

def read_input_file(input_path):
    """Read input JSON file."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found at: {path.absolute()}")
    with open(path, "r") as f:
        return json.load(f)

def extract_references(references):
    """Extract likely paper titles from references using regex."""
    extracted_titles = []
    for ref in references:
        # Regex handles double and single quotes safely
        match = re.search(r"[“\"'']([^”\"'']+)[”\"'']", ref)
        if match:
            extracted_titles.append(match.group(1).strip())
        else:
            extracted_titles.append(ref.split(".")[0].strip())
    return extracted_titles

def verify_citation_with_semantic_scholar(title):
    """Verify citation using Semantic Scholar API."""
    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_API,
            params={"query": title, "limit": 1, "fields": "title,abstract,year"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("total", 0) > 0:
                return data["data"][0], "verified"
        elif response.status_code == 429:
            return None, "rate_limit"
    except Exception as e:
        return None, f"error: {e}"
    return None, "fake_or_not_found"

def verify_citation_with_crossref(title):
    """Fallback to Crossref API."""
    try:
        response = requests.get(
            CROSSREF_API,
            params={"query": title},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            if items:
                return items[0], "verified"
    except Exception as e:
        return None, f"error: {e}"
    return None, "fake_or_not_found"

def verify_citations(references):
    """Verify all citations with rate-limit handling."""
    results = []
    extracted_titles = extract_references(references)
    for idx, (ref, title) in enumerate(zip(references, extracted_titles)):
        logging.info(f"Checking citation {idx+1}: {title}")
        
        paper, status = verify_citation_with_semantic_scholar(title)
        
        if status in ["rate_limit", "fake_or_not_found"]:
            if status == "rate_limit":
                logging.warning("Rate limit hit on Semantic Scholar, trying Crossref...")
            paper, status = verify_citation_with_crossref(title)
        
        results.append({
            "reference_id": idx + 1,
            "raw_reference": ref,
            "extracted_title": title,
            "status": status,
            "matched_paper": paper
        })
        time.sleep(1) # 1s delay to avoid blocking
    return results

def analyze_claims_with_groq(claims):
    """Analyze claims using the Llama 3.1 model."""
    results = []
    if not GROQ_API_KEY:
        logging.error("GROQ_API_KEY missing from .env file.")
        return results

    for idx, claim in enumerate(claims):
        try:
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a research integrity assistant."},
                    {"role": "user", "content": claim}
                ],
                "temperature": 0.2
            }
            response = requests.post(
                GROQ_API_ENDPOINT,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=20
            )
            if response.status_code == 200:
                data = response.json()
                analysis = data['choices'][0]['message']['content']
                results.append({"claim_id": idx + 1, "claim_text": claim, "analysis": analysis})
                logging.info(f"Groq analyzed claim {idx + 1}")
            else:
                logging.error(f"Groq Error {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"Groq connection failed: {e}")
    return results

def generate_assessment(citations, claims, groq_results):
    """
    CRITICAL: This function is required by api.py
    Generates the final JSON structure for the response.
    """
    verified_count = len([c for c in citations if c["status"] == "verified"])
    
    return {
        "overall_status": "green" if verified_count == len(citations) else "red",
        "verified_percentage": round((verified_count / len(citations) * 100), 2) if citations else 0,
        "citation_details": citations,
        "groq_analysis": groq_results
    }

def run_citation_agent(input_path, output_path, groq_output_path):
    """Main execution logic for CLI use."""
    paper_data = read_input_file(input_path)
    references = paper_data.get("references", [])
    
    # 1. Verify Citations
    citations = verify_citations(references)

    # 2. Prepare Claims
    claims = [
        f"{section.capitalize()}: {paper_data.get(section, '')}"
        for section in ["abstract", "results", "conclusion"]
        if paper_data.get(section)
    ]
    
    # 3. Groq Analysis
    groq_results = analyze_claims_with_groq(claims) if claims else []

    # 4. Generate Final Assessment
    assessment = generate_assessment(citations, claims, groq_results)

    # 5. Save results
    out_p, groq_p = Path(output_path), Path(groq_output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    groq_p.parent.mkdir(parents=True, exist_ok=True)

    with open(out_p, "w") as f:
        json.dump(assessment, f, indent=2)
    with open(groq_p, "w") as f:
        json.dump(groq_results, f, indent=2)

    print(f"\n✅ Finished! Summary: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="sample_input.json")
    parser.add_argument("--output", default="./results/output.json")
    parser.add_argument("--groq_output", default="./results/groq_output.json")
    args = parser.parse_args()
    run_citation_agent(args.input, args.output, args.groq_output)