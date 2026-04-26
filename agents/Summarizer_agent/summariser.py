from groq import Groq
import os
import re
from dotenv import load_dotenv
load_dotenv()
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
   raise ValueError("GROQ_API_KEY not found in .env")
client = Groq(api_key=api_key)

def clean_text(text):
   if not text:
       return ""
   text = re.sub(r'\s+', ' ', text)
   return text.strip()

def summarize_paper(data):
   try:
       title = clean_text(data.get("title", ""))
       abstract = clean_text(data.get("abstract", ""))[:1500]
       methodology = clean_text(data.get("methodology", ""))[:3000]
       results = clean_text(data.get("results", ""))[:1500]
       conclusion = clean_text(data.get("conclusion", ""))[:1000]
       prompt = f"""Summarize the following research paper into 350 words.
Rules:
- No JSON
- No bullet points
- No markdown
- Just plain text paragraph
Paper:
Title: {title}
Abstract: {abstract}
Methodology: {methodology}
Results: {results}
Conclusion: {conclusion}
"""
       response = client.chat.completions.create(
           model=MODEL_NAME,
           messages=[
               {"role": "user", "content": prompt}
           ],
           temperature=0.2,
           max_tokens=800
       )
       text = response.choices[0].message.content
       return {
           "summary": text.strip()
       }
   except Exception as e:
       print("Error:", e)
       return {
           "summary": "Failed to generate summary"
       }