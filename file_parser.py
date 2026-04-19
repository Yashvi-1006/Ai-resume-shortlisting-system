"""
File parsing utilities for PDF and DOCX files
Extracts text from various resume formats
"""

import pdfplumber
from docx import Document
from io import BytesIO


def extract_text_from_pdf(file_stream):
    """
    Extract text from PDF file.
    
    Args:
        file_stream: BytesIO or file-like object containing PDF
        
    Returns:
        str: Extracted text from all pages
    """
    try:
        text = ""
        with pdfplumber.open(file_stream) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
                text += "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")


def extract_text_from_docx(file_stream):
    """
    Extract text from DOCX file.
    
    Args:
        file_stream: BytesIO or file-like object containing DOCX
        
    Returns:
        str: Extracted text from all paragraphs
    """
    try:
        doc = Document(file_stream)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading DOCX: {str(e)}")


def extract_text_from_file(uploaded_file):
    """
    Extract text from uploaded file (PDF, DOCX, or TXT).
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        tuple: (text: str, filename: str, success: bool, message: str)
    """
    filename = uploaded_file.name
    file_extension = filename.split('.')[-1].lower()
    
    try:
        if file_extension == 'pdf':
            text = extract_text_from_pdf(uploaded_file)
        elif file_extension in ['docx', 'doc']:
            text = extract_text_from_docx(uploaded_file)
        elif file_extension == 'txt':
            text = uploaded_file.read().decode('utf-8')
        else:
            return "", filename, False, f"❌ Unsupported file format: .{file_extension}. Use PDF, DOCX, DOC, or TXT."
        
        if not text.strip():
            return "", filename, False, "⚠️ File is empty or no text could be extracted."
        
        return text, filename, True, f"✅ Successfully extracted text from {filename}"
    
    except Exception as e:
        return "", filename, False, f"❌ Error processing file: {str(e)}"


def batch_extract_from_files(uploaded_files):
    """
    Extract text from multiple uploaded files.
    
    Args:
        uploaded_files: List of Streamlit UploadedFile objects
        
    Returns:
        list: List of dicts with 'filename', 'text', 'success', 'message'
    """
    results = []
    for file in uploaded_files:
        text, filename, success, message = extract_text_from_file(file)
        results.append({
            'filename': filename,
            'text': text,
            'success': success,
            'message': message
        })
    return results
