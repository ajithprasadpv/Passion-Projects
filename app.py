import os
import logging
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from utils.file_parser import parse_questions_from_file
import tempfile

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret_key_for_development")

# Configure file upload settings
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_session_data(session_id):
    """Load questions and answers from temporary files"""
    questions_file = os.path.join(app.config['UPLOAD_FOLDER'], f'questions_{session_id}.json')
    answers_file = os.path.join(app.config['UPLOAD_FOLDER'], f'answers_{session_id}.json')
    
    try:
        with open(questions_file, 'r') as f:
            questions = json.load(f)
        
        with open(answers_file, 'r') as f:
            answer_key = json.load(f)
        
        return questions, answer_key
    except FileNotFoundError:
        return None, None

def cleanup_session_data(session_id):
    """Clean up temporary files for a session"""
    questions_file = os.path.join(app.config['UPLOAD_FOLDER'], f'questions_{session_id}.json')
    answers_file = os.path.join(app.config['UPLOAD_FOLDER'], f'answers_{session_id}.json')
    
    for file_path in [questions_file, answers_file]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

@app.route('/')
def index():
    """Home page with test configuration form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and test configuration"""
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        duration = request.form.get('duration', '30')
        positive_marks = request.form.get('positive_marks', '1')
        negative_marks = request.form.get('negative_marks', '0')
        feedback_mode = request.form.get('feedback_mode', 'final')
        
        # Validate required fields
        if not name:
            flash('Name is required', 'error')
            return redirect(url_for('index'))
        
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash('Invalid file format. Please upload PDF or DOCX files only.', 'error')
            return redirect(url_for('index'))
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parse questions from file
        try:
            questions, answer_key = parse_questions_from_file(filepath)
            
            if not questions:
                flash('No questions found in the uploaded file. Please ensure questions are in Q1, Q2... format.', 'error')
                os.remove(filepath)  # Clean up
                return redirect(url_for('index'))
            
            # Store questions and answers in temporary files to avoid session size limits
            import uuid
            session_id = str(uuid.uuid4())
            
            questions_file = os.path.join(app.config['UPLOAD_FOLDER'], f'questions_{session_id}.json')
            answers_file = os.path.join(app.config['UPLOAD_FOLDER'], f'answers_{session_id}.json')
            
            with open(questions_file, 'w') as f:
                json.dump(questions, f)
            
            with open(answers_file, 'w') as f:
                json.dump(answer_key, f)
            
            # Store only essential data in session
            session['test_config'] = {
                'name': name,
                'duration': int(duration),
                'positive_marks': float(positive_marks),
                'negative_marks': float(negative_marks),
                'feedback_mode': feedback_mode,
                'total_questions': len(questions),
                'session_id': session_id
            }
            
            # Initialize test state
            session['test_state'] = {
                'current_question': 0,
                'answers': {},
                'start_time': None,
                'completed': False
            }
            
            # Clean up uploaded file
            os.remove(filepath)
            
            flash(f'Successfully loaded {len(questions)} questions. Starting test...', 'success')
            return redirect(url_for('start_test'))
            
        except Exception as e:
            logging.error(f"Error parsing file: {str(e)}")
            flash(f'Error parsing file: {str(e)}', 'error')
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(url_for('index'))
    
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        flash('An error occurred during file upload', 'error')
        return redirect(url_for('index'))

@app.route('/test')
def start_test():
    """Start the test interface"""
    if 'test_config' not in session:
        flash('Please upload a test file first', 'error')
        return redirect(url_for('index'))
    
    # Initialize start time if not set
    if session['test_state']['start_time'] is None:
        import time
        session['test_state']['start_time'] = time.time()
        session.modified = True
    
    return render_template('test.html', 
                         config=session['test_config'],
                         state=session['test_state'])

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Handle answer submission"""
    if 'test_config' not in session or 'test_state' not in session:
        return jsonify({'error': 'Test session not found'}), 400
    
    try:
        question_num = int(request.form.get('question_num', 0))
        answer = request.form.get('answer', '')
        
        # Store answer (use string key for consistency)
        session['test_state']['answers'][str(question_num)] = answer
        session.modified = True
        
        config = session['test_config']
        state = session['test_state']
        
        # Check if immediate feedback is enabled
        if config['feedback_mode'] == 'immediate':
            questions, answer_key = load_session_data(config['session_id'])
            if answer_key:
                correct_answer = answer_key.get(str(question_num + 1), '')
                is_correct = answer.upper() == correct_answer.upper()
                
                return jsonify({
                    'success': True,
                    'feedback': {
                        'correct': is_correct,
                        'correct_answer': correct_answer,
                        'user_answer': answer
                    }
                })
            else:
                return jsonify({'error': 'Session data not found'}), 500
        
        return jsonify({'success': True})
    
    except Exception as e:
        logging.error(f"Error submitting answer: {str(e)}")
        return jsonify({'error': 'Failed to submit answer'}), 500

@app.route('/next_question', methods=['POST'])
def next_question():
    """Move to next question"""
    if 'test_state' not in session:
        return jsonify({'error': 'Test session not found'}), 400
    
    state = session['test_state']
    config = session['test_config']
    
    state['current_question'] = min(state['current_question'] + 1, 
                                   config['total_questions'] - 1)
    session.modified = True
    
    return jsonify({
        'success': True,
        'current_question': state['current_question']
    })

@app.route('/previous_question', methods=['POST'])
def previous_question():
    """Move to previous question"""
    if 'test_state' not in session:
        return jsonify({'error': 'Test session not found'}), 400
    
    state = session['test_state']
    state['current_question'] = max(state['current_question'] - 1, 0)
    session.modified = True
    
    return jsonify({
        'success': True,
        'current_question': state['current_question']
    })

@app.route('/get_question/<int:question_num>')
def get_question(question_num):
    """Get specific question data"""
    if 'test_config' not in session:
        return jsonify({'error': 'Test session not found'}), 400
    
    config = session['test_config']
    questions, _ = load_session_data(config['session_id'])
    
    if not questions or question_num < 0 or question_num >= len(questions):
        return jsonify({'error': 'Question not found'}), 404
    
    return jsonify({
        'success': True,
        'question': questions[question_num]
    })

@app.route('/submit_test', methods=['POST'])
def submit_test():
    """Submit the complete test"""
    if 'test_config' not in session or 'test_state' not in session:
        flash('Test session not found', 'error')
        return redirect(url_for('index'))
    
    # Mark test as completed
    session['test_state']['completed'] = True
    session.modified = True
    
    return redirect(url_for('results'))

@app.route('/results')
def results():
    """Display test results"""
    if 'test_config' not in session or 'test_state' not in session:
        flash('Test session not found', 'error')
        return redirect(url_for('index'))
    
    if not session['test_state']['completed']:
        flash('Please complete the test first', 'error')
        return redirect(url_for('start_test'))
    
    config = session['test_config']
    state = session['test_state']
    
    # Calculate results
    results = calculate_results(config, state)
    
    return render_template('results.html', 
                         config=config,
                         state=state,
                         results=results)

def calculate_results(config, state):
    """Calculate test results with scoring"""
    results = {
        'total_questions': config['total_questions'],
        'attempted': len(state['answers']),
        'correct': 0,
        'incorrect': 0,
        'unanswered': 0,
        'total_score': 0,
        'percentage': 0,
        'question_results': []
    }
    
    # Load questions and answers from session data
    questions, answer_key = load_session_data(config['session_id'])
    if not questions or not answer_key:
        logging.error("Failed to load session data for results calculation")
        return results
    
    for i in range(config['total_questions']):
        question_num = i + 1
        user_answer = state['answers'].get(str(i), '')
        correct_answer = answer_key.get(str(question_num), '')
        
        if not user_answer:
            status = 'unanswered'
            score = 0
            results['unanswered'] += 1
        elif user_answer.upper() == correct_answer.upper():
            status = 'correct'
            score = config['positive_marks']
            results['correct'] += 1
        else:
            status = 'incorrect'
            score = -config['negative_marks']
            results['incorrect'] += 1
        
        results['total_score'] += score
        
        results['question_results'].append({
            'question_num': question_num,
            'question': questions[i] if i < len(questions) else {},
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'status': status,
            'score': score
        })
    
    # Calculate percentage
    max_possible_score = config['total_questions'] * config['positive_marks']
    if max_possible_score > 0:
        results['percentage'] = max(0, (results['total_score'] / max_possible_score) * 100)
    
    return results

@app.route('/restart')
def restart():
    """Clear session and restart"""
    # Clean up session data files if they exist
    if 'test_config' in session and 'session_id' in session['test_config']:
        cleanup_session_data(session['test_config']['session_id'])
    
    session.clear()
    flash('Test session cleared. You can start a new test.', 'info')
    return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Please upload a file smaller than 16MB.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
