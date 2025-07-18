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
    
    # Split text at "Answer Key" section
    parts = re.split(r'(?i)answer\s*key', text, maxsplit=1)
    
    if len(parts) < 2:
        # No answer key found, try to extract questions only
        questions_text = parts[0]
        answer_text = ""
    else:
        questions_text = parts[0]
        answer_text = parts[1]
    
    # Extract questions
    questions = extract_questions_list(questions_text)
    
    # Extract answer key
    if answer_text:
        answer_key = extract_answer_key(answer_text)
    
    return questions, answer_key

def extract_questions_list(text: str) -> List[Dict]:
    """Extract individual questions with options from text"""
    questions = []
    
    # Pattern to match questions starting with Q1., Q2., etc.
    question_pattern = r'Q(\d+)\.?\s*(.*?)(?=Q\d+\.|\Z)'
    question_matches = re.findall(question_pattern, text, re.DOTALL | re.IGNORECASE)
    
    for match in question_matches:
        question_num = int(match[0])
        question_text = match[1].strip()
        
        # Extract question and options
        question_data = parse_single_question(question_text)
        if question_data:
            question_data['number'] = question_num
            questions.append(question_data)
    
    return questions

def parse_single_question(text: str) -> Optional[Dict]:
    """Parse a single question with its options"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        return None
    
    # First line(s) should be the question
    question_text = ""
    option_start_idx = len(lines)
    
    # Find where options start (A), B), C), D))
    for i, line in enumerate(lines):
        if re.match(r'^[A-D]\)', line, re.IGNORECASE):
            option_start_idx = i
            break
    
    # Join lines before options as question text
    question_text = " ".join(lines[:option_start_idx]).strip()
    
    # Extract options
    options = {}
    for line in lines[option_start_idx:]:
        option_match = re.match(r'^([A-D])\)\s*(.*)', line, re.IGNORECASE)
        if option_match:
            option_letter = option_match.group(1).upper()
            option_text = option_match.group(2).strip()
            options[option_letter] = option_text
    
    # Validate we have a question and at least 2 options
    if not question_text or len(options) < 2:
        return None
    
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

if __name__ == "__main__":
    # Run test
    test_parsing()
