import os
import logging
from PyPDF2 import PdfReader
from docx import Document
import mimetypes

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.allowed_extensions = {'pdf', 'docx', 'doc', 'txt'}
        self.max_file_size = 16 * 1024 * 1024  # 16MB
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def extract_text(self, filepath):
        """Extract text from uploaded document"""
        try:
            file_extension = filepath.rsplit('.', 1)[1].lower()
            
            if file_extension == 'pdf':
                return self._extract_pdf_text(filepath)
            elif file_extension in ['docx', 'doc']:
                return self._extract_docx_text(filepath)
            elif file_extension == 'txt':
                return self._extract_txt_text(filepath)
            else:
                return "Unsupported file format"
                
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            return "Error extracting text from document"
    
    def _extract_pdf_text(self, filepath):
        """Extract text from PDF file"""
        try:
            text = ""
            with open(filepath, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return "Error reading PDF file"
    
    def _extract_docx_text(self, filepath):
        """Extract text from DOCX file"""
        try:
            doc = Document(filepath)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return "Error reading DOCX file"
    
    def _extract_txt_text(self, filepath):
        """Extract text from TXT file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as file:
                    return file.read().strip()
            except Exception as e:
                logger.error(f"TXT extraction error: {e}")
                return "Error reading text file"
        except Exception as e:
            logger.error(f"TXT extraction error: {e}")
            return "Error reading text file"
    
    def validate_file_size(self, file):
        """Validate file size"""
        if hasattr(file, 'content_length') and file.content_length:
            return file.content_length <= self.max_file_size
        return True  # Allow if we can't determine size
    
    def get_file_info(self, filepath):
        """Get file information"""
        try:
            stat = os.stat(filepath)
            file_info = {
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'extension': filepath.rsplit('.', 1)[1].lower() if '.' in filepath else '',
                'mime_type': mimetypes.guess_type(filepath)[0]
            }
            return file_info
        except Exception as e:
            logger.error(f"File info error: {e}")
            return {}