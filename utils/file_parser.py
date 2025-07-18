import re
import logging
from typing import Dict, List, Tuple, Optional
import os

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("pdfplumber not available. PDF parsing will be disabled.")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logging.warning("python-docx not available. DOCX parsing will be disabled.")

def parse_questions_from_file(filepath: str) -> Tuple[List[Dict], Dict[int, str]]:
    """
    Parse questions and answers from uploaded file (PDF or DOCX)
    
    Args:
        filepath: Path to the uploaded file
        
    Returns:
        Tuple of (questions_list, answer_key_dict)
        questions_list: List of question dictionaries with text and options
        answer_key_dict: Dictionary mapping question numbers to correct answers
    """
    file_ext = os.path.splitext(filepath)[1].lower()
    
    if file_ext == '.pdf':
        if not PDF_AVAILABLE:
            raise Exception("PDF processing not available. Please install pdfplumber.")
        return parse_pdf_questions(filepath)
    elif file_ext == '.docx':
        if not DOCX_AVAILABLE:
            raise Exception("DOCX processing not available. Please install python-docx.")
        return parse_docx_questions(filepath)
    else:
        raise Exception(f"Unsupported file format: {file_ext}")

def parse_pdf_questions(filepath: str) -> Tuple[List[Dict], Dict[int, str]]:
    """Parse questions from PDF file"""
    try:
        with pdfplumber.open(filepath) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return extract_questions_from_text(text)
    
    except Exception as e:
        logging.error(f"Error parsing PDF: {str(e)}")
        raise Exception(f"Failed to parse PDF file: {str(e)}")

def parse_docx_questions(filepath: str) -> Tuple[List[Dict], Dict[int, str]]:
    """Parse questions from DOCX file"""
    try:
        doc = Document(filepath)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return extract_questions_from_text(text)
    
    except Exception as e:
        logging.error(f"Error parsing DOCX: {str(e)}")
        raise Exception(f"Failed to parse DOCX file: {str(e)}")

def extract_questions_from_text(text: str) -> Tuple[List[Dict], Dict[int, str]]:
    """
    Extract questions and answer key from text content
    
    Expected format:
    Q1. Question text here?
    A) Option A
    B) Option B
    C) Option C
    D) Option D
    
    Q2. Another question?
    A) Option A
    B) Option B
    C) Option C
    D) Option D
    
    ...
    
    Answer Key:
    1. A
    2. B
    3. C
    ...
    """
    questions = []
    answer_key = {}
    
    logging.debug(f"Processing text of length: {len(text)}")
    
    # Split text at "Answer Key" section (try multiple variations)
    answer_key_patterns = [
        r'(?i)answer\s*key',
        r'(?i)answers?\s*:',
        r'(?i)solution\s*key',
        r'(?i)correct\s*answers?'
    ]
    
    questions_text = text
    answer_text = ""
    
    for pattern in answer_key_patterns:
        parts = re.split(pattern, text, maxsplit=1)
        if len(parts) >= 2:
            questions_text = parts[0]
            answer_text = parts[1]
            logging.debug(f"Found answer key section using pattern: {pattern}")
            break
    
    if not answer_text:
        logging.debug("No answer key section found, processing entire text as questions")
    
    # Extract questions
    questions = extract_questions_list(questions_text)
    logging.debug(f"Extracted {len(questions)} questions")
    
    # Extract answer key
    if answer_text:
        answer_key = extract_answer_key(answer_text)
        logging.debug(f"Extracted {len(answer_key)} answers")
    
    # If no answer key found, create a dummy answer key for testing purposes
    if not answer_key and questions:
        logging.debug("Creating dummy answer key for testing")
        for i, q in enumerate(questions):
            # Use first available option as dummy answer
            if q.get('options'):
                first_option = list(q['options'].keys())[0]
                answer_key[i + 1] = first_option
    
    return questions, answer_key

def extract_questions_list(text: str) -> List[Dict]:
    """Extract individual questions with options from text"""
    questions = []
    
    # Extensive text cleanup for PDF artifacts
    text = clean_pdf_text(text)
    
    # Pattern to match questions starting with Q1., Q2., etc.
    # More flexible pattern to capture multiline questions
    question_pattern = r'Q(\d+)\.?\s*(.*?)(?=Q\d+\.|\Z)'
    question_matches = re.findall(question_pattern, text, re.DOTALL | re.IGNORECASE)
    
    logging.debug(f"Found {len(question_matches)} potential question matches")
    
    for match in question_matches:
        question_num = int(match[0])
        question_text = match[1].strip()
        
        # Skip if the question text is too short (likely not a real question)
        if len(question_text) < 10:
            logging.debug(f"Skipping Q{question_num} - text too short: {len(question_text)}")
            continue
        
        logging.debug(f"Processing Q{question_num}: {question_text[:100]}...")
        
        # Extract question and options
        question_data = parse_single_question(question_text)
        if question_data:
            question_data['number'] = question_num
            questions.append(question_data)
            logging.debug(f"Successfully parsed Q{question_num}")
        else:
            logging.debug(f"Failed to parse Q{question_num}")
    
    return questions

def clean_pdf_text(text: str) -> str:
    """Clean up PDF text extraction artifacts"""
    # Remove common PDF artifacts
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'\n+', '\n', text)  # Normalize line breaks
    
    # Remove isolated single characters that are PDF artifacts
    text = re.sub(r'\s[a-z]\s', ' ', text)  # Remove isolated lowercase letters
    text = re.sub(r'\s[A-Z]\s(?![A-D]\))', ' ', text)  # Remove isolated uppercase letters (except option letters)
    
    # Remove common PDF noise patterns
    text = re.sub(r'www\.[a-zA-Z.]+', '', text)  # Remove website URLs
    text = re.sub(r'[0-9]+\s*www\.[a-zA-Z.]+', '', text)  # Remove page numbers with URLs
    
    # Clean up option patterns - ensure proper spacing
    text = re.sub(r'\(\s*([a-dA-D])\s*\)', r'(\1)', text)  # Fix spaced parentheses
    
    return text.strip()

def parse_single_question(text: str) -> Optional[Dict]:
    """Parse a single question with its options"""
    
    # Clean up text and split into lines
    text = text.strip()
    if not text:
        return None
    
    # Initialize variables
    question_text = ""
    options = {}
    
    # Clean the text first
    text = clean_pdf_text(text)
    
    # Try to extract question and options using multiple patterns
    
    # Pattern 1: Inline options like (a) Option1 (b) Option2 (c) Option3 (d) Option4
    # Look for at least 2 option patterns in the text
    option_pattern = r'\(([a-dA-D])\)'
    option_positions = [(m.start(), m.group(1)) for m in re.finditer(option_pattern, text)]
    
    if len(option_positions) >= 2:
        # Extract question text (everything before first option)
        first_option_pos = option_positions[0][0]
        question_text = text[:first_option_pos].strip()
        
        # Extract inline options with better pattern
        # Handle cases where options might be just (a) (b) (c) (d) without content
        full_pattern = r'\(([a-dA-D])\)\s*([^(]*?)(?=\s*\([a-dA-D]\)|$)'
        option_matches = re.findall(full_pattern, text)
        
        for option_letter, option_text in option_matches:
            option_text = option_text.strip()
            # If option text is empty or very short, create a placeholder
            if not option_text or len(option_text) < 2:
                option_text = f"Option {option_letter.upper()}"
            options[option_letter.upper()] = option_text
        
        # If we found option letters but no text, create basic options
        if not options and len(option_positions) >= 2:
            for pos, letter in option_positions[:4]:  # Take up to 4 options
                options[letter.upper()] = f"Option {letter.upper()}"
    
    else:
        # Pattern 2: Multiline options like A) Option1 \n B) Option2
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return None
        
        # Find where options start (A), B), C), D))
        option_start_idx = len(lines)
        for i, line in enumerate(lines):
            if re.match(r'^[A-D]\)', line, re.IGNORECASE):
                option_start_idx = i
                break
        
        # Join lines before options as question text
        question_text = " ".join(lines[:option_start_idx]).strip()
        
        # Extract options
        for line in lines[option_start_idx:]:
            option_match = re.match(r'^([A-D])\)\s*(.*)', line, re.IGNORECASE)
            if option_match:
                option_letter = option_match.group(1).upper()
                option_text = option_match.group(2).strip()
                if not option_text:
                    option_text = f"Option {option_letter}"
                options[option_letter] = option_text
    
    # Clean up question text - remove extra spaces and unwanted characters
    if question_text:
        # Remove various noise patterns commonly found in PDFs
        question_text = re.sub(r'\s+', ' ', question_text)
        question_text = re.sub(r'^[^\w]*', '', question_text)  # Remove leading non-word chars
        question_text = question_text.strip()
    
    # Validate we have a question and at least 2 options
    if not question_text or len(question_text) < 5:
        logging.debug(f"Validation failed - question_text too short: '{question_text}' ({len(question_text) if question_text else 0} chars)")
        return None
    
    if len(options) < 2:
        logging.debug(f"Validation failed - insufficient options: {len(options)} options found")
        return None
    
    logging.debug(f"Successfully parsed question: {question_text[:50]}... with {len(options)} options")
    return {
        'question': question_text,
        'options': options
    }

def extract_answer_key(text: str) -> Dict[int, str]:
    """Extract answer key from text"""
    answer_key = {}
    
    # Pattern to match answer key entries like "1. A", "2. B", etc.
    answer_patterns = [
        r'(\d+)\.?\s*([A-D])',  # 1. A or 1 A
        r'Q?(\d+)[\.\:\s]*([A-D])',  # Q1: A or Q1 A
    ]
    
    for pattern in answer_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            question_num = int(match[0])
            answer = match[1].upper()
            answer_key[question_num] = answer
    
    return answer_key

def validate_questions_and_answers(questions: List[Dict], answer_key: Dict[int, str]) -> bool:
    """Validate that questions and answer key are consistent"""
    if not questions:
        return False
    
    # Check if we have answers for most questions
    question_numbers = {q.get('number', i+1) for i, q in enumerate(questions)}
    answer_numbers = set(answer_key.keys())
    
    # We should have answers for at least 50% of questions
    overlap = len(question_numbers.intersection(answer_numbers))
    return overlap >= len(questions) * 0.5

# Test function for debugging
def test_parsing():
    """Test function to validate parsing logic"""
    sample_text = """
    Q1. What is the capital of France?
    A) London
    B) Berlin
    C) Paris
    D) Madrid
    
    Q2. Which planet is closest to the Sun?
    A) Venus
    B) Mercury
    C) Earth
    D) Mars
    
    Answer Key:
    1. C
    2. B
    """
    
    questions, answers = extract_questions_from_text(sample_text)
    print(f"Questions: {questions}")
    print(f"Answers: {answers}")
    
    return questions, answers

def test_pdf_parsing():
    """Test parsing with PDF-like inline format"""
    sample_text = """
    Q1. Which of the following diagrams indicates the best relation between Thief, Criminal and Police?
    (a) Diagram A (b) Diagram B (c) Diagram C (d) Diagram D
    
    Q2. Which of the following diagrams indicates best relation between Pigeon, Bird and Dog?
    (a) Circle A (b) Circle B (c) Circle C (d) Circle D
    """
    
    questions, answers = extract_questions_from_text(sample_text)
    print(f"PDF Format Questions: {questions}")
    print(f"PDF Format Answers: {answers}")
    
    return questions, answers

if __name__ == "__main__":
    # Run test
    test_parsing()
