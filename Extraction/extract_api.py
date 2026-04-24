import re
import os
import tempfile
import pdfplumber
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

app = FastAPI(title="Dynamic Research Paper Extractor")

class ExtractionResult(BaseModel):
    title: str
    authors: List[str]
    sections: Dict[str, str]
    references: List[str]

def clean_text(text: str) -> str:
    """Fixes hyphenation and extra whitespace."""
    if not text: return ""
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_metadata_by_font(page):
    """
    Dynamically identifies the Title and Authors based on font size.
    Title = Largest font on page 1.
    Authors = Text appearing after title with a consistent 'author' font size.
    """
    chars = page.chars
    if not chars:
        return "Unknown Title", []
    max_size = max(c['size'] for c in chars)
    
    title_chars = [c['text'] for c in chars if abs(c['size'] - max_size) < 0.1]
    title = "".join(title_chars).strip()

    sizes = sorted(list(set(round(c['size'], 2) for c in chars)), reverse=True)
    
    potential_authors = []
    if len(sizes) > 1:
        blacklist = ['university', 'school', 'department', 'engineering', 'india', 'kalan', 'abstract']
        
        for size in sizes[1:4]: 
            text_block = "".join([c['text'] for c in chars if abs(round(c['size'], 2) - size) < 0.1])
            
            names = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z\.]+)+', text_block)
            
            for name in names:
                if not any(word in name.lower() for word in blacklist):
                    if name not in potential_authors:
                        potential_authors.append(name)
            
            if potential_authors: break # Found author block

    return clean_text(title), potential_authors

def extract_smart_columns(page):
    """Handles 2-column layouts by splitting the page vertically."""
    width = page.width
    height = page.height
    mid = width / 2
    
    left_bbox = (0, 0, mid, height)
    left_text = page.within_bbox(left_bbox).extract_text() or ""
    
    right_bbox = (mid, 0, width, height)
    right_text = page.within_bbox(right_bbox).extract_text() or ""
    
    return left_text + "\n" + right_text

def segment_sections(full_text: str):
    """Splits content into sections based on standard headers."""
    header_pattern = r'\n\s*(?:(?:[IVXLC]+\.|[0-9]+\.)\s+)?([A-Z]{4,}(?:\s+[A-Z]{4,})*)'
    
    sections = {}
    
    abstract_match = re.search(r'Abstract[—\-\s]+(.*?)(?=I\.\s+INTRODUCTION|Keywords|II\.)', full_text, re.DOTALL | re.IGNORECASE)
    if abstract_match:
        sections["ABSTRACT"] = clean_text(abstract_match.group(1))

    matches = list(re.finditer(header_pattern, full_text))
    for i in range(len(matches)):
        current_match = matches[i]
        title = current_match.group(1).strip()
        start = current_match.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(full_text)
        sections[title] = clean_text(full_text[start:end])
        
    return sections

@app.post("/extract", response_model=ExtractionResult)
async def process_paper(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported.")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        all_text = ""
        dynamic_title = ""
        dynamic_authors = []

        with pdfplumber.open(tmp_path) as pdf:
            dynamic_title, dynamic_authors = get_metadata_by_font(pdf.pages[0])
            
            for page in pdf.pages:
                all_text += extract_smart_columns(page) + "\n"

        sections_dict = segment_sections(all_text)
        
        ref_content = sections_dict.get("REFERENCES", "")
        references = [r.strip() for r in re.split(r'\[\d+\]', ref_content) if len(r) > 10]

        return {
            "title": dynamic_title or "Untitled Document",
            "authors": dynamic_authors,
            "sections": sections_dict,
            "references": references
        }

    except Exception as e:
        raise HTTPException(500, f"Extraction failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)