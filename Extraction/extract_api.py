from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pdfplumber
import re
import json
import tempfile
import os
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(
    title="Research Paper Extraction API",
    description="Extract structured content from research papers in PDF format",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for response
class Metadata(BaseModel):
    authors: List[str]
    publication_year: Optional[int]
    journal: str
    doi: str

class ExtractionResult(BaseModel):
    title: str
    abstract: str
    methodology: str
    results: str
    conclusion: str
    references: List[str]
    metadata: Metadata

# Extraction functions
def extract_two_column_text(page):
    """Extract text from a two-column page layout"""
    width = page.width
    height = page.height
    mid_point = width / 2
    overlap = 20
    
    left_bbox = (0, 0, mid_point + overlap, height)
    left_column = page.crop(left_bbox)
    
    right_bbox = (mid_point - overlap, 0, width, height)
    right_column = page.crop(right_bbox)
    
    left_text = left_column.extract_text() or ""
    right_text = right_column.extract_text() or ""
    
    combined_text = left_text.strip() + "\n" + right_text.strip()
    return combined_text

def find_all_sections(text):
    """Find all section headers using regex"""
    sections = []
    section_names = [
        "abstract", "introduction", "methodology", "methods",
        "materials and methods", "results", "conclusion", "conclusions",
        "acknowledgement", "acknowledgment", "acknowledgements",
        "acknowledgments", "references", "discussion",
        "literature review", "related work", "background", "future work"
    ]
    
    for section_name in section_names:
        patterns = [
            r'\n\s*' + re.escape(section_name) + r'\s*\n',
            r'\n\s*(?:\d+\.?|[IVX]+\.?)\s*' + re.escape(section_name) + r'\s*\n',
            r'\n\s*' + re.escape(section_name) + r'\s*:\s*',
            r'\n\s*' + re.escape(section_name.upper()) + r'\s*\n',
            r'\n\s*(?:\d+\.?|[IVX]+\.?)\s*' + re.escape(section_name.upper()) + r'\s*\n',
            r'\n' + re.escape(section_name) + r'\s*\n',
            r'\n' + re.escape(section_name.upper()) + r'\s*\n',
            r'\n\s*' + re.escape(section_name.title()) + r'\s*\n',
            r'\n\s*(?:\d+\.?|[IVX]+\.?)\s*' + re.escape(section_name.title()) + r'\s*\n',
            r'\n\s*' + re.escape(section_name.upper()) + r'\s*:\s*',
            r'\n\s*' + re.escape(section_name.title()) + r'\s*:\s*'
        ]
        
        found = False
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sections.append({
                    'name': section_name.lower(),
                    'start': match.start(),
                    'end': match.end(),
                    'matched_text': match.group().strip()
                })
                found = True
                break
        
        if not found:
            pattern = r'\b' + re.escape(section_name) + r'\b'
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                line_start = text.rfind('\n', 0, match.start())
                if line_start == -1:
                    line_start = 0
                line_end = text.find('\n', match.end())
                if line_end == -1:
                    line_end = len(text)
                
                line = text[line_start:line_end].strip()
                
                if len(line) < 60 and not line.endswith('.'):
                    sections.append({
                        'name': section_name.lower(),
                        'start': match.start(),
                        'end': line_end,
                        'matched_text': line
                    })
                    break
    
    sections.sort(key=lambda x: x['start'])
    
    seen_names = set()
    unique_sections = []
    for section in sections:
        if section['name'] not in seen_names:
            seen_names.add(section['name'])
            unique_sections.append(section)
    
    return unique_sections

def extract_section_by_name(text, sections, section_name):
    """Extract content for a specific section"""
    section_name = section_name.lower()
    
    alternative_names = {
        'methodology': ['methodology', 'methods', 'materials and methods'],
        'conclusion': ['conclusion', 'conclusions'],
        'acknowledgement': ['acknowledgement', 'acknowledgment', 'acknowledgements', 'acknowledgments']
    }
    
    search_names = alternative_names.get(section_name, [section_name])
    
    section_index = None
    for i, section in enumerate(sections):
        if section['name'] in search_names:
            section_index = i
            break
    
    if section_index is None:
        return ""
    
    start_pos = sections[section_index]['end']
    
    if section_index + 1 < len(sections):
        end_pos = sections[section_index + 1]['start']
    else:
        end_pos = len(text)
    
    content = text[start_pos:end_pos].strip()
    content = clean_section_content(content)
    
    return content

def extract_references_by_section(text, sections):
    """Extract references as an array"""
    ref_section = None
    for section in sections:
        if section['name'] == 'references':
            ref_section = section
            break
    
    if not ref_section:
        return []
    
    start_pos = ref_section['end']
    
    end_pos = len(text)
    for section in sections:
        if section['start'] > ref_section['start']:
            end_pos = section['start']
            break
    
    ref_text = text[start_pos:end_pos].strip()
    
    if not ref_text:
        return []
    
    references = []
    refs = re.split(r'\n\s*\[\d+\]\s*', ref_text)
    
    if len(refs) <= 1:
        refs = re.split(r'\n\s*\d+\.\s+', ref_text)
    
    if len(refs) <= 1:
        refs = re.split(r'\n\s*\[[A-Z][a-z]+\s+\d{4}\]\s*', ref_text)
    
    if len(refs) <= 1:
        refs = re.split(r'\n(?=[A-Z][a-z]+[,\s])', ref_text)
    
    for ref in refs:
        ref = ref.strip()
        ref = re.sub(r'\s+', ' ', ref)
        
        if len(ref) > 20 and not re.match(r'^\d+$', ref):
            references.append(ref)
    
    return references[:100]

def clean_section_content(content):
    """Clean extracted section content"""
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    content = re.sub(r'\n\s*\d+\s*\n', '\n', content)
    content = re.sub(r'\n\s*Page\s+\d+\s*\n', '\n', content, flags=re.IGNORECASE)
    content = re.sub(r' +', ' ', content)
    
    lines = content.split('\n')
    lines = [line.strip() for line in lines]
    content = '\n'.join(lines)
    
    return content.strip()

def add_spaces_to_title(title):
    """Add spaces between concatenated words"""
    if not title:
        return title
    
    spaced_title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)
    spaced_title = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced_title)
    spaced_title = re.sub(r'\s+', ' ', spaced_title)
    
    return spaced_title.strip()

def extract_title_by_font_size(first_page):
    """Extract title by font size"""
    try:
        chars = first_page.chars
        
        if not chars:
            return ""
        
        page_height = first_page.height
        title_region_chars = [c for c in chars if c.get('top', 0) < page_height * 0.3]
        
        if not title_region_chars:
            title_region_chars = chars[:500]
        
        lines_by_size = {}
        current_line = []
        last_top = None
        last_size = None
        
        for char in title_region_chars:
            size = round(char.get('size', 0), 1)
            top = round(char.get('top', 0), 1)
            text = char.get('text', '')
            
            if last_top is not None and abs(top - last_top) > 2:
                if current_line and last_size:
                    if last_size not in lines_by_size:
                        lines_by_size[last_size] = []
                    line_text = ''.join(current_line).strip()
                    if line_text:
                        lines_by_size[last_size].append(line_text)
                current_line = []
            
            current_line.append(text)
            last_top = top
            last_size = size
        
        if current_line and last_size:
            if last_size not in lines_by_size:
                lines_by_size[last_size] = []
            line_text = ''.join(current_line).strip()
            if line_text:
                lines_by_size[last_size].append(line_text)
        
        if not lines_by_size:
            return ""
        
        max_font_size = max(lines_by_size.keys())
        title_lines = lines_by_size[max_font_size]
        title = ' '.join(title_lines)
        title = re.sub(r'\s+', ' ', title).strip()
        
        if len(title) < 10 or len(title) > 300:
            sorted_sizes = sorted(lines_by_size.keys(), reverse=True)
            if len(sorted_sizes) > 1:
                second_largest = sorted_sizes[1]
                title = ' '.join(lines_by_size[second_largest])
                title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    except Exception as e:
        print(f"Error extracting title by font size: {e}")
        return ""

def extract_title_fallback(text):
    """Fallback title extraction"""
    lines = text.split('\n')
    
    for line in lines[:15]:
        line = line.strip()
        if 20 < len(line) < 200 and re.search(r'[a-zA-Z]', line):
            if not re.search(r'@|http|doi|volume|issue|page', line.lower()):
                return line
    
    return ""

def extract_authors_advanced(text):
    """Extract authors"""
    header = text[:1200]
    authors = []
    
    email_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+).*?@'
    email_authors = re.findall(email_pattern, header)
    authors.extend(email_authors)
    
    affiliation_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+).*?(?:University|Institute|Department|College)'
    affiliation_authors = re.findall(affiliation_pattern, header)
    authors.extend(affiliation_authors)
    
    lines = header.split('\n')
    for line in lines[:25]:
        line = line.strip()
        if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', line):
            authors.append(line)
        elif re.match(r'^[A-Z][a-z]+,\s+[A-Z]', line):
            authors.append(line)
    
    seen = set()
    unique_authors = []
    for author in authors:
        author_clean = author.strip()
        if author_clean and author_clean not in seen and len(author_clean) > 3:
            seen.add(author_clean)
            unique_authors.append(author_clean)
    
    return unique_authors[:15]

def extract_doi(text):
    """Extract DOI"""
    doi_patterns = [
        r'doi:\s*(10\.\d{4,}/[^\s]+)',
        r'DOI:\s*(10\.\d{4,}/[^\s]+)',
        r'https?://doi\.org/(10\.\d{4,}/[^\s]+)',
        r'\bdoi\s+(10\.\d{4,}/[^\s]+)'
    ]
    
    for pattern in doi_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doi = match.group(1).strip()
            doi = re.sub(r'[,.\s]+$', '', doi)
            return doi
    
    return ""

def extract_year(text):
    """Extract publication year"""
    header = text[:1500]
    years = re.findall(r'\b(19\d{2}|20\d{2})\b', header)
    
    if years:
        return int(max(years))
    
    return None

def extract_journal(text):
    """Extract journal name"""
    header = text[:1000]
    lines = header.split('\n')
    
    journal_keywords = ['journal', 'proceedings', 'conference', 'transactions', 'letters', 'review', 'symposium']
    
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in journal_keywords):
            journal = line.strip()
            if 10 < len(journal) < 150:
                return journal
    
    return ""

def extract_research_paper_advanced(pdf_path):
    """Main extraction function"""
    output = {
        "title": "",
        "abstract": "",
        "methodology": "",
        "results": "",
        "conclusion": "",
        "references": [],
        "metadata": {
            "authors": [],
            "publication_year": None,
            "journal": "",
            "doi": ""
        }
    }
    
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) > 0:
            output["title"] = extract_title_by_font_size(pdf.pages[0])
        
        for page in pdf.pages:
            text = extract_two_column_text(page)
            if text:
                full_text += text + "\n"
    
    if not output["title"]:
        output["title"] = extract_title_fallback(full_text)
    
    output["title"] = add_spaces_to_title(output["title"])
    
    sections = find_all_sections(full_text)
    
    output["abstract"] = extract_section_by_name(full_text, sections, "abstract")
    output["methodology"] = extract_section_by_name(full_text, sections, "methodology")
    output["results"] = extract_section_by_name(full_text, sections, "results")
    output["conclusion"] = extract_section_by_name(full_text, sections, "conclusion")
    output["references"] = extract_references_by_section(full_text, sections)
    
    output["metadata"]["doi"] = extract_doi(full_text)
    output["metadata"]["publication_year"] = extract_year(full_text)
    output["metadata"]["authors"] = extract_authors_advanced(full_text)
    output["metadata"]["journal"] = extract_journal(full_text)
    
    return output

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Research Paper Extraction API",
        "version": "1.0.0",
        "endpoints": {
            "POST /extract": "Extract content from PDF",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/extract", response_model=ExtractionResult)
async def extract_pdf(file: UploadFile = File(...)):
    """
    Extract structured content from a research paper PDF
    
    - **file**: PDF file to extract content from
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create temporary file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            # Write uploaded file to temporary file
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Extract content
        result = extract_research_paper_advanced(tmp_file_path)
        
        # Clean up temporary file
        os.unlink(tmp_file_path)
        
        return result
    
    except Exception as e:
        # Clean up temporary file if it exists
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/extract-json")
async def extract_pdf_json(file: UploadFile = File(...)):
    """
    Extract structured content from a research paper PDF and return as JSON
    
    - **file**: PDF file to extract content from
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        result = extract_research_paper_advanced(tmp_file_path)
        
        os.unlink(tmp_file_path)
        
        return JSONResponse(content=result)
    
    except Exception as e:
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)