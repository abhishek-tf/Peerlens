import pdfplumber
import re
import json

def extract_research_paper_advanced(pdf_path):
    """
    Advanced extraction for two-column PDFs with robust regex section detection
    """
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
    
    # Extract text handling two-column layout
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        # Extract title from first page using font size
        if len(pdf.pages) > 0:
            output["title"] = extract_title_by_font_size(pdf.pages[0])
        
        # Extract all text with two-column handling
        for page in pdf.pages:
            text = extract_two_column_text(page)
            if text:
                full_text += text + "\n"
    
    # If title not found by font size, use fallback
    if not output["title"]:
        output["title"] = extract_title_fallback(full_text)
    
    # Add spaces to title if needed
    output["title"] = add_spaces_to_title(output["title"])
    
    # Find all section positions using regex
    sections = find_all_sections(full_text)
    
    # Debug: Print found sections
    print("\n🔍 Found sections:")
    if sections:
        for section in sections:
            print(f"  • {section['name'].upper()} at position {section['start']} - matched: '{section['matched_text']}'")
    else:
        print("  ⚠️  No sections found!")
    
    # Extract content for each section
    output["abstract"] = extract_section_by_name(full_text, sections, "abstract")
    output["methodology"] = extract_section_by_name(full_text, sections, "methodology")
    output["results"] = extract_section_by_name(full_text, sections, "results")
    output["conclusion"] = extract_section_by_name(full_text, sections, "conclusion")
    
    # Extract references separately (as array)
    output["references"] = extract_references_by_section(full_text, sections)
    
    # Extract metadata
    output["metadata"]["doi"] = extract_doi(full_text)
    output["metadata"]["publication_year"] = extract_year(full_text)
    output["metadata"]["authors"] = extract_authors_advanced(full_text)
    output["metadata"]["journal"] = extract_journal(full_text)
    
    return output

def extract_two_column_text(page):
    """
    Extract text from a two-column page layout with improved overlap handling
    """
    # Get page dimensions
    width = page.width
    height = page.height
    
    # Define column boundaries with increased overlap for better capture
    mid_point = width / 2
    overlap = 20  # Increased overlap to ensure no content is missed
    
    # Crop left column
    left_bbox = (0, 0, mid_point + overlap, height)
    left_column = page.crop(left_bbox)
    
    # Crop right column
    right_bbox = (mid_point - overlap, 0, width, height)
    right_column = page.crop(right_bbox)
    
    # Extract text from each column
    left_text = left_column.extract_text() or ""
    right_text = right_column.extract_text() or ""
    
    # Combine columns: left column first, then right column
    # Strip to remove extra whitespace and ensure clean concatenation
    combined_text = left_text.strip() + "\n" + right_text.strip()
    
    return combined_text

def find_all_sections(text):
    """
    Find all section headers and their positions using regex (case-insensitive)
    Enhanced with more robust pattern matching
    """
    sections = []
    
    # Define section names to search for (expanded list)
    section_names = [
        "abstract",
        "introduction", 
        "methodology",
        "methods",
        "materials and methods",
        "results",
        "conclusion",
        "conclusions",
        "acknowledgement",
        "acknowledgment",
        "acknowledgements",
        "acknowledgments",
        "references",
        "discussion",
        "literature review",
        "related work",
        "background",
        "future work"
    ]
    
    for section_name in section_names:
        # Create multiple patterns to catch different formats
        patterns = [
            # Pattern 1: Section name on its own line (with optional whitespace)
            r'\n\s*' + re.escape(section_name) + r'\s*\n',
            
            # Pattern 2: Section name with optional numbering (1. Abstract, I. Abstract, etc.)
            r'\n\s*(?:\d+\.?|[IVX]+\.?)\s*' + re.escape(section_name) + r'\s*\n',
            
            # Pattern 3: Section name with colon (Abstract:)
            r'\n\s*' + re.escape(section_name) + r'\s*:\s*',
            
            # Pattern 4: Section name in all caps
            r'\n\s*' + re.escape(section_name.upper()) + r'\s*\n',
            
            # Pattern 5: Section name with optional numbering in all caps
            r'\n\s*(?:\d+\.?|[IVX]+\.?)\s*' + re.escape(section_name.upper()) + r'\s*\n',
            
            # Pattern 6: Section name at start of line (less strict)
            r'\n' + re.escape(section_name) + r'\s*\n',
            
            # Pattern 7: Section name in all caps at start of line
            r'\n' + re.escape(section_name.upper()) + r'\s*\n',
            
            # Pattern 8: Handle title case (e.g., "Literature Review")
            r'\n\s*' + re.escape(section_name.title()) + r'\s*\n',
            
            # Pattern 9: With optional numbering in title case
            r'\n\s*(?:\d+\.?|[IVX]+\.?)\s*' + re.escape(section_name.title()) + r'\s*\n',
            
            # Pattern 10: Section name with colon in all caps
            r'\n\s*' + re.escape(section_name.upper()) + r'\s*:\s*',
            
            # Pattern 11: Section name with colon in title case
            r'\n\s*' + re.escape(section_name.title()) + r'\s*:\s*'
        ]
        
        found = False
        for pattern in patterns:
            # Search case-insensitively
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
        
        # If standard patterns don't work, try a more lenient search
        if not found:
            # Just look for the word with word boundaries
            pattern = r'\b' + re.escape(section_name) + r'\b'
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                # Check if it's likely a section header (on a short line)
                line_start = text.rfind('\n', 0, match.start())
                if line_start == -1:
                    line_start = 0
                line_end = text.find('\n', match.end())
                if line_end == -1:
                    line_end = len(text)
                
                line = text[line_start:line_end].strip()
                
                # If the line is short and mostly just the section name, consider it a header
                # Also check if it's not part of a longer sentence
                if len(line) < 60 and not line.endswith('.'):
                    sections.append({
                        'name': section_name.lower(),
                        'start': match.start(),
                        'end': line_end,
                        'matched_text': line
                    })
                    break
    
    # Sort sections by position
    sections.sort(key=lambda x: x['start'])
    
    # Remove duplicates (keep first occurrence)
    seen_names = set()
    unique_sections = []
    for section in sections:
        if section['name'] not in seen_names:
            seen_names.add(section['name'])
            unique_sections.append(section)
    
    return unique_sections

def extract_section_by_name(text, sections, section_name):
    """
    Extract content for a specific section by name
    Enhanced to handle edge cases better
    """
    section_name = section_name.lower()
    
    # Find the section (also check for alternative names)
    section_index = None
    alternative_names = {
        'methodology': ['methodology', 'methods', 'materials and methods'],
        'conclusion': ['conclusion', 'conclusions'],
        'acknowledgement': ['acknowledgement', 'acknowledgment', 'acknowledgements', 'acknowledgments']
    }
    
    search_names = alternative_names.get(section_name, [section_name])
    
    for i, section in enumerate(sections):
        if section['name'] in search_names:
            section_index = i
            break
    
    if section_index is None:
        return ""
    
    # Get start position (after the section header)
    start_pos = sections[section_index]['end']
    
    # Get end position (start of next section, or end of text)
    if section_index + 1 < len(sections):
        end_pos = sections[section_index + 1]['start']
    else:
        end_pos = len(text)
    
    # Extract content
    content = text[start_pos:end_pos].strip()
    
    # Clean up the content
    content = clean_section_content(content)
    
    return content

def extract_references_by_section(text, sections):
    """
    Extract references as an array of strings
    """
    # Find references section
    ref_section = None
    for section in sections:
        if section['name'] == 'references':
            ref_section = section
            break
    
    if not ref_section:
        return []
    
    # Get start position
    start_pos = ref_section['end']
    
    # Get end position (end of document or next section)
    end_pos = len(text)
    for section in sections:
        if section['start'] > ref_section['start']:
            end_pos = section['start']
            break
    
    # Extract references text
    ref_text = text[start_pos:end_pos].strip()
    
    if not ref_text:
        return []
    
    # Split references by different patterns
    references = []
    
    # Pattern 1: [1], [2], etc.
    refs = re.split(r'\n\s*\[\d+\]\s*', ref_text)
    
    # Pattern 2: 1., 2., etc.
    if len(refs) <= 1:
        refs = re.split(r'\n\s*\d+\.\s+', ref_text)
    
    # Pattern 3: [Author Year] format
    if len(refs) <= 1:
        refs = re.split(r'\n\s*\[[A-Z][a-z]+\s+\d{4}\]\s*', ref_text)
    
    # Pattern 4: Author names at start of line
    if len(refs) <= 1:
        refs = re.split(r'\n(?=[A-Z][a-z]+[,\s])', ref_text)
    
    # Clean and filter references
    for ref in refs:
        ref = ref.strip()
        ref = re.sub(r'\s+', ' ', ref)
        
        # Filter out very short strings and page numbers
        if len(ref) > 20 and not re.match(r'^\d+$', ref):
            references.append(ref)
    
    return references[:100]

def clean_section_content(content):
    """
    Clean extracted section content
    """
    # Remove excessive whitespace
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # Remove standalone page numbers
    content = re.sub(r'\n\s*\d+\s*\n', '\n', content)
    
    # Remove page headers/footers (common patterns)
    content = re.sub(r'\n\s*Page\s+\d+\s*\n', '\n', content, flags=re.IGNORECASE)
    
    # Normalize spaces
    content = re.sub(r' +', ' ', content)
    
    # Remove leading/trailing whitespace from each line
    lines = content.split('\n')
    lines = [line.strip() for line in lines]
    content = '\n'.join(lines)
    
    return content.strip()

def add_spaces_to_title(title):
    """
    Add spaces between concatenated words in title
    """
    if not title:
        return title
    
    # Add space before capital letters that follow lowercase letters
    spaced_title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)
    
    # Add space before capital letters in sequences like "AIenhanced"
    spaced_title = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced_title)
    
    # Clean up multiple spaces
    spaced_title = re.sub(r'\s+', ' ', spaced_title)
    
    return spaced_title.strip()

def extract_title_by_font_size(first_page):
    """
    Extract title by identifying the largest font size text on first page
    """
    try:
        chars = first_page.chars
        
        if not chars:
            return ""
        
        # Analyze first 30% of the page
        page_height = first_page.height
        title_region_chars = [c for c in chars if c.get('top', 0) < page_height * 0.3]
        
        if not title_region_chars:
            title_region_chars = chars[:500]
        
        # Group by font size and line
        lines_by_size = {}
        current_line = []
        last_top = None
        last_size = None
        
        for char in title_region_chars:
            size = round(char.get('size', 0), 1)
            top = round(char.get('top', 0), 1)
            text = char.get('text', '')
            
            # Check if we're on a new line
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
        
        # Save last line
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
        
        # Validate and try second largest if needed
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
    """
    Fallback method if font-based extraction fails
    """
    lines = text.split('\n')
    
    for line in lines[:15]:
        line = line.strip()
        if 20 < len(line) < 200 and re.search(r'[a-zA-Z]', line):
            if not re.search(r'@|http|doi|volume|issue|page', line.lower()):
                return line
    
    return ""

def extract_authors_advanced(text):
    """
    Advanced author extraction
    """
    header = text[:1200]
    authors = []
    
    # Pattern 1: Email addresses often near author names
    email_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+).*?@'
    email_authors = re.findall(email_pattern, header)
    authors.extend(email_authors)
    
    # Pattern 2: Names before affiliations
    affiliation_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+).*?(?:University|Institute|Department|College)'
    affiliation_authors = re.findall(affiliation_pattern, header)
    authors.extend(affiliation_authors)
    
    # Pattern 3: Simple name pattern in first 25 lines
    lines = header.split('\n')
    for line in lines[:25]:
        line = line.strip()
        # Match "Firstname Lastname" pattern
        if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', line):
            authors.append(line)
        # Match "Lastname, Firstname" pattern
        elif re.match(r'^[A-Z][a-z]+,\s+[A-Z]', line):
            authors.append(line)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_authors = []
    for author in authors:
        author_clean = author.strip()
        if author_clean and author_clean not in seen and len(author_clean) > 3:
            seen.add(author_clean)
            unique_authors.append(author_clean)
    
    return unique_authors[:15]

def extract_doi(text):
    """
    Extract DOI from text
    """
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
    """
    Extract publication year from header
    """
    header = text[:1500]
    years = re.findall(r'\b(19\d{2}|20\d{2})\b', header)
    
    if years:
        return int(max(years))
    
    return None

def extract_journal(text):
    """
    Extract journal name
    """
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

# Main execution
if __name__ == "__main__":
    pdf_path = "research_paper.pdf"
    
    print("Extracting two-column research paper with enhanced section detection...")
    print("=" * 70)
    
    result = extract_research_paper_advanced(pdf_path)
    
    # Save to JSON
    with open("structured_paper.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("\n✓ Extraction complete!")
    print("=" * 70)
    print(f"\n📄 Title:\n   {result['title']}")
    print(f"\n📊 Extracted Content:")
    print(f"  • Abstract: {len(result['abstract'])} characters")
    if result['abstract']:
        print(f"    Preview: {result['abstract'][:150]}...")
    print(f"\n  • Methodology: {len(result['methodology'])} characters")
    if result['methodology']:
        print(f"    Preview: {result['methodology'][:150]}...")
    print(f"\n  • Results: {len(result['results'])} characters")
    if result['results']:
        print(f"    Preview: {result['results'][:150]}...")
    print(f"\n  • Conclusion: {len(result['conclusion'])} characters")
    if result['conclusion']:
        print(f"    Preview: {result['conclusion'][:150]}...")
    print(f"\n  • References: {len(result['references'])} items")
    if result['references']:
        print(f"    First reference: {result['references'][0][:100]}...")
    
    print(f"\n👥 Metadata:")
    print(f"  • Authors: {', '.join(result['metadata']['authors']) if result['metadata']['authors'] else 'Not found'}")
    print(f"  • Year: {result['metadata']['publication_year']}")
    print(f"  • DOI: {result['metadata']['doi'] if result['metadata']['doi'] else 'Not found'}")
    print(f"  • Journal: {result['metadata']['journal'] if result['metadata']['journal'] else 'Not found'}")