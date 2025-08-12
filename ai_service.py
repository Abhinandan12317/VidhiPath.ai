import logging
import os
from dotenv import load_dotenv
import requests
import torch
import re

logger = logging.getLogger(__name__)

class AIService:
    def format_plain(self, text):
        """
        Remove all bold/italic/HTML/asterisk formatting from AI output for plain text display.
        """
        if not isinstance(text, str):
            return text
        # Remove HTML bold/strong tags
        text = re.sub(r'<\/?(b|strong|em)>', '', text, flags=re.IGNORECASE)
        # Remove asterisks used for markdown bold/italic
        text = re.sub(r'\*+', '', text)
        # Remove stray underscores (for _italic_)
        text = re.sub(r'_+', '', text)
        # Remove any remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()
    def __init__(self):
        load_dotenv()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        # Summarization model is not loaded by default
        self.summarization_model = None
        # Gemini API key from .env
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def generate_legal_response(self, message):
        """Generate legal guidance response using Gemini API"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"As a legal assistant for Indian law, provide helpful guidance for this question: {message}\n\nPlease provide accurate information based on Indian legal framework and suggest consulting with a qualified lawyer for specific cases."
                            }
                        ]
                    }
                ]
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Gemini API response: {result}")

            # Try to extract text from all known Gemini API response structures
            # 1. Standard 'contents' structure
            if (
                isinstance(result, dict)
                and 'contents' in result
                and isinstance(result['contents'], list)
                and len(result['contents']) > 0
                and 'parts' in result['contents'][0]
                and isinstance(result['contents'][0]['parts'], list)
                and len(result['contents'][0]['parts']) > 0
                and 'text' in result['contents'][0]['parts'][0]
            ):
                return result['contents'][0]['parts'][0]['text']

            # 2. 'candidates' structure (Gemini sometimes returns this)
            if (
                isinstance(result, dict)
                and 'candidates' in result
                and isinstance(result['candidates'], list)
                and len(result['candidates']) > 0
            ):
                candidate = result['candidates'][0]
                if (
                    isinstance(candidate, dict)
                    and 'content' in candidate
                    and isinstance(candidate['content'], dict)
                    and 'parts' in candidate['content']
                    and isinstance(candidate['content']['parts'], list)
                    and len(candidate['content']['parts']) > 0
                    and 'text' in candidate['content']['parts'][0]
                ):
                    return candidate['content']['parts'][0]['text']
            # 3. Try to find any 'text' field in a nested structure (future-proof fallback)
            def find_text_field(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == 'text' and isinstance(v, str):
                            return v
                        found = find_text_field(v)
                        if found:
                            return found
                elif isinstance(obj, list):
                    for item in obj:
                        found = find_text_field(item)
                        if found:
                            return found
                return None

            fallback_text = find_text_field(result)
            if fallback_text:
                logger.warning(f"Gemini API: Used fallback text extraction. Structure: {result}")
                return fallback_text

            logger.error(f"Unexpected Gemini API response structure: {result}")
            return "Sorry, I couldn't generate a response. Please try again later."
        except Exception as e:
            logger.error(f"Error generating legal response: {e}")
            return "I apologize, but I'm unable to process your request at the moment. Please consult with a qualified legal professional for personalized advice."
    
    def _generate_fallback_legal_response(self, message):
        """Generate fallback legal response when AI model is not available"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ['fir', 'police', 'complaint']):
            return """Regarding FIR (First Information Report):
            
1. You have the right to file an FIR for cognizable offenses
2. Police cannot refuse to register FIR for cognizable crimes
3. If police refuse, approach the Superintendent of Police
4. You can also file a complaint directly with a Magistrate
5. Keep a copy of the FIR for your records

Please consult with a qualified lawyer for specific legal advice regarding your situation."""
        
        elif any(keyword in message_lower for keyword in ['rti', 'information']):
            return """Regarding RTI (Right to Information):
            
1. RTI Act 2005 gives citizens right to access government information
2. File RTI application with concerned Public Information Officer (PIO)
3. Fee is usually ₹10 for general category applicants
4. Information should be provided within 30 days
5. File first appeal if information is denied or delayed

Please consult the official RTI portal or a legal expert for detailed guidance."""
        
        elif any(keyword in message_lower for keyword in ['property', 'registration', 'sale deed']):
            return """Regarding Property matters:
            
1. Verify property documents thoroughly before purchase
2. Check for clear title and encumbrance certificate
3. Property registration is mandatory for legal ownership
4. Pay applicable stamp duty and registration fees
5. Ensure all taxes are cleared

Please consult with a qualified property lawyer and get professional legal advice for your specific property transaction."""
        
        else:
            return """Thank you for your legal query. Based on Indian legal framework:
            
1. Always verify your rights under applicable laws
2. Maintain proper documentation for any legal matter
3. Seek timely legal remedy if rights are violated
4. Consider alternative dispute resolution methods when appropriate
5. Consult with qualified legal professionals for personalized advice

Please note that this is general guidance only. For specific legal advice, please consult with a qualified lawyer who can review your particular circumstances."""
    
    def validate_document(self, text_content):
        """Validate legal document"""
        try:
            if not text_content or len(text_content.strip()) < 50:
                return {
                    'status': 'invalid',
                    'issues': ['Document content is too short or empty'],
                    'summary': 'Document validation failed due to insufficient content.'
                }
            
            issues = []
            
            # Check for common legal document elements
            if not re.search(r'\b(witness|signature|date|party|agreement|contract)\b', text_content, re.IGNORECASE):
                issues.append('Missing standard legal document elements (witness, signature, date, etc.)')
            
            # Check for date formats
            if not re.search(r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b', text_content):
                issues.append('No valid date format found in document')
            
            # Check for signature indication
            if not re.search(r'\b(sign|signature|signed)\b', text_content, re.IGNORECASE):
                issues.append('No signature indication found')
            
            # Check document length
            if len(text_content.split()) < 100:
                issues.append('Document appears to be unusually short for a legal document')
            
            status = 'valid' if len(issues) == 0 else 'issues_found'
            summary = f"Document validation completed. {len(issues)} issues found." if issues else "Document appears to be properly formatted."
            
            return {
                'status': status,
                'issues': issues,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Document validation error: {e}")
            return {
                'status': 'error',
                'issues': ['Unable to validate document due to processing error'],
                'summary': 'Document validation failed due to technical error.'
            }
    
    def predict_case_outcome(self, case_details):
        """Predict case outcome and provide analysis, including progress bar percent and formatted output."""
        try:
            case_type = case_details.get('case_type', '').lower()
            location = case_details.get('location', '')
            year_filed = case_details.get('year_filed', '')
            description = case_details.get('description', '')

            # Generate prediction based on case type and details
            success_result = self._calculate_success_probability(case_type, description)
            prediction = {
                'success_probability': success_result.get('formatted', ''),
                'success_percent': success_result.get('percent', 0),
                'estimated_duration': self._estimate_duration(case_type, location),
                'recommended_jurisdiction': self._recommend_jurisdiction(case_type, location),
                'key_factors': self._identify_key_factors(case_type, description),
                'next_steps': self._suggest_next_steps(case_type)
            }
            return prediction
        except Exception as e:
            logger.error(f"Case prediction error: {e}")
            return {
                'success_probability': 'Unable to determine',
                'success_percent': 0,
                'estimated_duration': 'Unable to estimate',
                'recommended_jurisdiction': 'Please consult with a lawyer',
                'key_factors': ['Consult with qualified legal professional'],
                'next_steps': ['Seek legal advice from qualified attorney']
            }
    
    def _calculate_success_probability(self, case_type, description):
        """AI-based: Calculate success probability using Gemini API. Returns dict with percent and formatted string."""
        try:
            prompt = (
                f"Hi! I'm Vidhi, your friendly legal assistant. Based on the following case details, estimate the probability of success in a warm, helpful, and conversational tone. "
                f"Case type: {case_type}\n"
                f"Case description: {description}\n"
                "Give your answer as a percentage probability (e.g., 'Success Probability: 65%') and a brief, friendly reason. If you cannot estimate, say so. Sign off as Vidhi."
            )
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            ai_text = None
            if 'contents' in result and result['contents'] and 'parts' in result['contents'][0] and result['contents'][0]['parts']:
                ai_text = result['contents'][0]['parts'][0].get('text', "No response generated.")
            elif 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                    ai_text = candidate['content']['parts'][0].get('text', "No response generated.")
            if ai_text is not None:
                formatted = self.format_bold(ai_text.strip())
                percent = self._extract_percent_from_text(ai_text)
                return {"percent": percent, "formatted": formatted, "raw": ai_text.strip()}
            logger.error(f"Unexpected Gemini API response: {result}")
            return {"percent": 0, "formatted": "Sorry, Vidhi couldn't estimate the success probability at this time.", "raw": ""}
        except Exception as e:
            logger.error(f"AI-based success probability error: {e}")
            return {"percent": 0, "formatted": "I'm Vidhi, your friendly assistant. Unable to estimate success probability due to technical error.", "raw": ""}

    def _extract_percent_from_text(self, text):
        """Extracts the first percentage value from text, returns int (0-100) or 0 if not found."""
        import re
        match = re.search(r'(\d{1,3})\s*%|([0-9]{1,3})\s*percent', text)
        if match:
            try:
                return int(match.group(1) or match.group(2))
            except Exception:
                return 0
        return 0

    def _estimate_duration(self, case_type, location, case_description=''):
        """AI-based: Estimate case duration using Gemini API."""
        try:
            prompt = (
                f"Hi! I'm Vidhi, your friendly legal assistant. Based on the following case details, estimate the likely duration for resolution in India. "
                f"Case type: {case_type}\n"
                f"Location: {location}\n"
                f"Case description: {case_description}\n"
                "Give your answer as a range (e.g., '1-2 years') and briefly mention the reasoning behind it."
            )
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            ai_text = None
            if 'contents' in result and result['contents'] and 'parts' in result['contents'][0] and result['contents'][0]['parts']:
                ai_text = result['contents'][0]['parts'][0].get('text', "No response generated.")
            elif 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                    ai_text = candidate['content']['parts'][0].get('text', "No response generated.")
            if ai_text is not None:
                return ai_text.strip()
            logger.error(f"Unexpected Gemini API response: {result}")
            return "Sorry, Vidhi couldn't estimate the case duration at this time."
        except Exception as e:
            logger.error(f"AI-based case duration error: {e}")
            return "I'm Vidhi, your friendly assistant. Unable to estimate case duration due to technical error."
    
    def _recommend_jurisdiction(self, case_type, location, case_summary=''):
        """AI-based: Recommend appropriate jurisdiction using Gemini API."""
        try:
            prompt = (
                f"Hi! I'm Vidhi, your friendly legal assistant. Based on the following case details, recommend the appropriate court jurisdiction in India. "
                f"Case type: {case_type}\n"
                f"Location: {location}\n"
                f"Case summary: {case_summary}\n"
                "Recommend the appropriate jurisdiction (e.g., Family Court, Sessions Court, Civil Court, Consumer Court, High Court, etc.). If unclear, suggest consulting a lawyer. Explain your reasoning in 1-2 lines."
            )
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            ai_text = None
            if 'contents' in result and result['contents'] and 'parts' in result['contents'][0] and result['contents'][0]['parts']:
                ai_text = result['contents'][0]['parts'][0].get('text', "No response generated.")
            elif 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                    ai_text = candidate['content']['parts'][0].get('text', "No response generated.")
            if ai_text is not None:
                return ai_text.strip()
            logger.error(f"Unexpected Gemini API response: {result}")
            return "Sorry, Vidhi couldn't recommend the jurisdiction at this time."
        except Exception as e:
            logger.error(f"AI-based jurisdiction error: {e}")
            return "I'm Vidhi, your friendly assistant. Unable to recommend jurisdiction due to technical error."
    
    def _identify_key_factors(self, case_type, description):
        """AI-based: Identify key factors affecting case using Gemini API."""
        try:
            prompt = (
                f"Hi! I'm Vidhi, your friendly legal assistant. Based on the following case details, list the key factors that will affect the outcome. "
                f"Case type: {case_type}\n"
                f"Case description: {description}\n"
                "List 3-5 key factors as bullet points."
            )
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            ai_text = None
            if 'contents' in result and result['contents'] and 'parts' in result['contents'][0] and result['contents'][0]['parts']:
                ai_text = result['contents'][0]['parts'][0].get('text', "No response generated.")
            elif 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                    ai_text = candidate['content']['parts'][0].get('text', "No response generated.")
            if ai_text is not None:
                # Return as a list of factors
                return [factor.strip('-• ') for factor in ai_text.strip().split('\n') if factor.strip()]
            logger.error(f"Unexpected Gemini API response: {result}")
            return ["Sorry, Vidhi couldn't identify key factors at this time."]
        except Exception as e:
            logger.error(f"AI-based key factors error: {e}")
            return ["Consult a qualified lawyer for key factors."]
    
    def _suggest_next_steps(self, case_type, case_description=''):
        """AI-based: Suggest next legal steps using Gemini API."""
        try:
            prompt = (
                f"Hi! I'm Vidhi, your friendly legal assistant. Based on the following case details, suggest the next 3–5 actionable legal steps a person should take in India. "
                f"Case type: {case_type}\n"
                f"Case description: {case_description}\n"
                "Keep the steps practical, sequenced, and relevant to the case type."
            )
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            ai_text = None
            if 'contents' in result and result['contents'] and 'parts' in result['contents'][0] and result['contents'][0]['parts']:
                ai_text = result['contents'][0]['parts'][0].get('text', "No response generated.")
            elif 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content'] and candidate['content']['parts']:
                    ai_text = candidate['content']['parts'][0].get('text', "No response generated.")
            if ai_text is not None:
                return [step.strip("-• ") for step in ai_text.strip().split("\n") if step.strip()]
            logger.error(f"Unexpected Gemini API response: {result}")
            return ["Sorry, Vidhi couldn't suggest next steps at this time."]
        except Exception as e:
            logger.error(f"AI-based next steps error: {e}")
            return ["Consult a qualified lawyer", "Gather all relevant documents"]
    
    def generate_summary(self, text_content):
        """Generate summary of case or legal text"""
        try:
            if not text_content or len(text_content.strip()) < 100:
                return "Text content is too short to generate a meaningful summary."
            
            if self.summarization_model:
                # Chunk text if too long
                max_chunk_length = 1024
                if len(text_content) > max_chunk_length:
                    chunks = [text_content[i:i+max_chunk_length] 
                             for i in range(0, len(text_content), max_chunk_length)]
                    summaries = []
                    
                    for chunk in chunks[:3]:  # Limit to first 3 chunks
                        try:
                            summary = self.summarization_model(
                                chunk, 
                                max_length=150, 
                                min_length=50, 
                                do_sample=False
                            )
                            summaries.append(summary[0]['summary_text'])
                        except Exception as e:
                            logger.error(f"Chunk summarization error: {e}")
                    
                    return " ".join(summaries) if summaries else "Unable to generate summary."
                else:
                    summary = self.summarization_model(
                        text_content, 
                        max_length=200, 
                        min_length=50, 
                        do_sample=False
                    )
                    return summary[0]['summary_text']
            else:
                # Fallback summary generation
                return self._generate_fallback_summary(text_content)
                
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return "Unable to generate summary due to processing error. Please try with shorter text or consult the original document."
    
    def _generate_fallback_summary(self, text_content):
        """Generate fallback summary when AI model is not available"""
        sentences = text_content.split('.')
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Take first few sentences and last sentence
        if len(sentences) > 5:
            summary_sentences = sentences[:3] + [sentences[-1]]
        else:
            summary_sentences = sentences[:len(sentences)//2 + 1]
        
        summary = '. '.join(summary_sentences)
        return f"Summary: {summary}. Note: This is an automated summary. Please review the full document for complete details."
    
    def format_bold(self, text):
        """
        Convert *text* and **text** in AI output to HTML <b> and <strong> tags for legibility.
        Ensures no stray asterisks or tags are left, for seamless reading.
        """
        if not isinstance(text, str):
            return text
        # Replace **bold** with <strong>bold</strong>
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Replace *italic* with <b>italic</b> (or use <em> if you prefer)
        text = re.sub(r'\*(?!\*)([^*]+?)\*', r'<b>\1</b>', text)
        # Remove any stray unmatched asterisks
        text = re.sub(r'\*+', '', text)
        # Remove any stray closing strong tags (in case of malformed input)
        text = text.replace('</Strong>', '</strong>')
        # Remove any double spaces or space before punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        return text.strip()