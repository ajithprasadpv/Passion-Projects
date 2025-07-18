# Mock Test Simulator

## Overview

This is a Flask-based web application that allows users to upload question papers (PDF/DOCX) and take timed mock tests with automatic scoring. The application parses uploaded documents to extract questions and answer keys, provides a timer-based test interface, and generates detailed results with feedback.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask
- **CSS Framework**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla JavaScript for timer functionality and client-side interactions
- **Icons**: Font Awesome for UI icons
- **Responsive Design**: Mobile-first approach using Bootstrap grid system

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Session Management**: Flask sessions for maintaining test state
- **File Handling**: Temporary file storage for uploaded documents
- **Logging**: Python logging module for debugging

### File Processing
- **PDF Parsing**: pdfplumber library for extracting text from PDF files
- **DOCX Parsing**: python-docx library for processing Word documents
- **Question Extraction**: Regular expressions for parsing question patterns and answer keys

## Key Components

### Core Application (`app.py`)
- Flask application configuration and routing
- File upload handling with security validation
- Session management for test configuration and progress
- Form validation and error handling

### Template System
- **Base Template**: Common layout with navigation and flash messages
- **Index Template**: Test configuration form with file upload
- **Test Template**: Question display with timer and navigation
- **Results Template**: Score display and detailed answer review

### File Parser (`utils/file_parser.py`)
- Document processing for PDF and DOCX formats
- Question and answer extraction using pattern matching
- Error handling for unsupported formats

### Frontend Assets
- **CSS**: Custom styling for timer, question navigation, and responsive design
- **JavaScript**: Timer functionality with countdown and auto-submit features

## Data Flow

1. **Test Setup**: User fills configuration form and uploads question paper
2. **File Processing**: Backend parses document to extract questions and answers
3. **Session Storage**: Test configuration and questions stored in Flask session
4. **Test Execution**: User navigates through questions with timer countdown
5. **Answer Collection**: User responses stored in session during test
6. **Results Generation**: Final scoring and detailed feedback display

## External Dependencies

### Python Libraries
- **Flask**: Web framework and routing
- **pdfplumber**: PDF text extraction (optional)
- **python-docx**: Word document processing (optional)
- **werkzeug**: File utilities and security

### Frontend Libraries
- **Bootstrap 5**: UI framework with dark theme
- **Font Awesome**: Icon library
- **Custom CSS/JS**: Timer and interaction enhancements

### Environment Configuration
- **SESSION_SECRET**: Environment variable for session security
- **File Upload**: Temporary directory storage with size limits (16MB)

## Deployment Strategy

### Configuration
- Environment-based secret key management
- Temporary file storage for uploaded documents
- Session-based state management (no persistent database)
- File type restrictions (PDF, DOCX only)

### Security Features
- Secure filename handling for uploads
- File extension validation
- Session secret key protection
- File size limits to prevent abuse

### Scalability Considerations
- Stateless design using sessions (can be moved to database)
- Temporary file cleanup
- No persistent data storage requirements
- Ready for containerization with minimal changes

### Production Readiness
- Logging configuration for debugging
- Error handling and user feedback
- Responsive design for mobile devices
- Clean separation of concerns between components