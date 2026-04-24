import requests
import json
 
# Your FastAPI endpoint URL
API_URL = "http://localhost:8000/api/v1/assess"
 
# The structured payload
payload = {
    "paper": {
        "title": "BizCollab: An AI-Powered Platform for Business Management",
        "abstract": "This paper presents BizCollab, an integrated platform...",
        "methodology": "We conducted a controlled within-subjects experiment with 10 participants to evaluate the effectiveness. We measured task completion time, accuracy, and user satisfaction.",
        "results": "Results showed significant improvements in task completion time.",
        "conclusion": "BizCollab demonstrates significant potential."
    },
    "pre_extracted_components": {
        "sample_info": {
            "sample_size": 10
        },
        "evaluation_metrics": [
            "Task completion time",
            "Accuracy",
            "User satisfaction"
        ]
    },
    "assessment_mode": "comprehensive"
}
 
print("🚀 Sending request to API...")
 
try:
    response = requests.post(API_URL, json=payload)
    
    # Check if the request was successful
    if response.status_code == 200:
        print("✅ Success! Here is the response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Failed with status code: {response.status_code}")
        print("Error details:", response.text)
 
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Is your FastAPI server running on port 8000?")
 