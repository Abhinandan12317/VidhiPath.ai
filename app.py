import os
import secrets
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
from datetime import datetime, timedelta
import jwt
import json
from functools import wraps
import logging
from ai_service import AIService
from database import DatabaseManager
from auth import AuthManager
from document_processor import DocumentProcessor

# For email sending
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
#from env
email_address = os.getenv("EMAIL_HOST_NAME")
email_password = os.getenv("'vqey jgeg mcke onxi'")

# For OTP storage (in-memory for demo; use DB for production)
otp_store = {}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
#for secret key loaded from env
app.secret_key = os.getenv("FLASK_SECRET_KEY")

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email config (replace with your SMTP server details)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', email_address)
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD',email_password )
EMAIL_USE_TLS = True

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services
db_manager = DatabaseManager()
auth_manager = AuthManager(db_manager)
ai_service = AIService()
document_processor = DocumentProcessor()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            user = auth_manager.get_user_by_id(session['user_id'])
            if not user or user['role'] not in roles:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Helper: send OTP email
def send_otp_email(to_email, otp):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_HOST_USER
        msg['To'] = to_email
        msg['Subject'] = 'Your OTP for Password Reset'
        body = f"Your OTP for password reset is: {otp}\nThis OTP is valid for 10 minutes."
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        if EMAIL_USE_TLS:
            server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.sendmail(EMAIL_HOST_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email: {str(e)}")
        return False
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip()
        user = auth_manager.get_user_by_email(email)
        if not user:
            flash('No account found with that email.', 'error')
            return render_template('forgot_password.html')

        # Generate OTP
        otp = str(secrets.randbelow(1000000)).zfill(6)
        expiry = datetime.now() + timedelta(minutes=10)
        otp_store[email] = {'otp': otp, 'expiry': expiry}

        # Send OTP email
        if send_otp_email(email, otp):
            session['reset_email'] = email
            flash('OTP sent to your email.', 'info')
            return redirect(url_for('verify_otp'))
        else:
            flash('Failed to send OTP. Try again later.', 'error')
    return render_template('forgot_password.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        otp_input = request.form['otp'].strip()
        otp_data = otp_store.get(email)
        if not otp_data or datetime.now() > otp_data['expiry']:
            flash('OTP expired. Please request a new one.', 'error')
            return redirect(url_for('forgot_password'))
        if otp_input == otp_data['otp']:
            session['otp_verified'] = True
            flash('OTP verified. Please set your new password.', 'success')
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid OTP.', 'error')
    return render_template('verify_otp.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')
    if not email or not session.get('otp_verified'):
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html')
        # Update password
        if auth_manager.update_user_password_by_email(email, new_password):
            # Clean up session and OTP
            session.pop('reset_email', None)
            session.pop('otp_verified', None)
            otp_store.pop(email, None)
            flash('Password reset successful. Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Failed to reset password.', 'error')
    return render_template('reset_password.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = auth_manager.authenticate_user(email, password)
        if user:
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')  # Default to 'user' if not provided
        
        if auth_manager.register_user(name, email, password, role):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Email might already exist.', 'error')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = db_manager.get_user_stats(session['user_id'])
    return render_template('dashboard.html', stats=stats)

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Generate AI response
        response = ai_service.generate_legal_response(message)
        
        # Save to database
        chat_id = db_manager.save_chat_log(session['user_id'], message, response)
        
        return jsonify({
            'response': response,
            'chat_id': chat_id,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return jsonify({'error': 'Failed to process request'}), 500

@app.route('/api/chat/history')
@login_required
def chat_history():
    try:
        history = db_manager.get_chat_history(session['user_id'])
        return jsonify(history)
    except Exception as e:
        logger.error(f"Chat history error: {str(e)}")
        return jsonify({'error': 'Failed to fetch chat history'}), 500

@app.route('/document-checker')
@login_required
def document_checker():
    return render_template('document_checker.html')

@app.route('/api/check-document', methods=['POST'])
@login_required
def check_document():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and document_processor.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process document
            text_content = document_processor.extract_text(filepath)
            validation_result = ai_service.validate_document(text_content)
            
            # Save to database
            doc_id = db_manager.save_document(session['user_id'], filename, 'checked', validation_result.get('summary', ''))
            
            return jsonify({
                'document_id': doc_id,
                'filename': filename,
                'validation_result': validation_result,
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({'error': 'Invalid file type'}), 400
    
    except Exception as e:
        logger.error(f"Document check error: {str(e)}")
        return jsonify({'error': 'Failed to process document'}), 500

@app.route('/case-prediction')
@login_required
def case_prediction():
    return render_template('case_prediction.html')

@app.route('/api/predict-case', methods=['POST'])
@login_required
def predict_case():
    try:
        data = request.get_json()
        case_details = {
            'case_type': data.get('case_type', ''),
            'year_filed': data.get('year_filed', ''),
            'location': data.get('location', ''),
            'description': data.get('description', '')
        }
        
        # Generate prediction
        prediction = ai_service.predict_case_outcome(case_details)
        
        # Save analysis
        analysis_id = db_manager.save_case_analysis(session['user_id'], case_details, prediction)
        
        return jsonify({
            'analysis_id': analysis_id,
            'prediction': prediction,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Case prediction error: {str(e)}")
        return jsonify({'error': 'Failed to predict case outcome'}), 500

@app.route('/case-summary')
@login_required
def case_summary():
    return render_template('case_summary.html')

@app.route('/api/summarize', methods=['POST'])
@login_required
def summarize_case():
    try:
        text_input = request.form.get('text_input', '').strip()
        file_content = ''
        
        # Handle file upload if present
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            if document_processor.allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                file_content = document_processor.extract_text(filepath)
        
        # Combine text inputs
        combined_text = f"{text_input}\n\n{file_content}".strip()
        
        if not combined_text:
            return jsonify({'error': 'No text provided for summarization'}), 400
        
        # Generate summary
        summary = ai_service.generate_summary(combined_text)
        
        return jsonify({
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Case summary error: {str(e)}")
        return jsonify({'error': 'Failed to generate summary'}), 500

@app.route('/knowledge-base')
def knowledge_base():
    try:
        categories = db_manager.get_faq_categories()
        faqs = db_manager.get_all_faqs()
        return render_template('knowledge_base.html', categories=categories, faqs=faqs)
    except Exception as e:
        logger.error(f"Knowledge base error: {str(e)}")
        return render_template('knowledge_base.html', categories=[], faqs=[])

@app.route('/api/search-faqs')
def search_faqs():
    try:
        query = request.args.get('q', '').strip()
        category = request.args.get('category', '')
        
        results = db_manager.search_faqs(query, category)
        return jsonify(results)
    
    except Exception as e:
        logger.error(f"FAQ search error: {str(e)}")
        return jsonify([])

@app.route('/saved-content')
@login_required
def saved_content():
    try:
        chat_history = db_manager.get_chat_history(session['user_id'])
        documents = db_manager.get_user_documents(session['user_id'])
        case_analyses = db_manager.get_user_case_analyses(session['user_id'])
        
        return render_template('saved_content.html', 
                             chat_history=chat_history,
                             documents=documents,
                             case_analyses=case_analyses)
    except Exception as e:
        logger.error(f"Saved content error: {str(e)}")
        return render_template('saved_content.html', 
                             chat_history=[], documents=[], case_analyses=[])

@app.route('/profile')
@login_required
def profile():
    user = auth_manager.get_user_by_id(session['user_id'])
    stats = db_manager.get_user_stats(session['user_id'])
    return render_template('profile.html', user=user, stats=stats)

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not name:
            return jsonify({'error': 'Name cannot be empty'}), 400
        
        # Update name
        success = auth_manager.update_user_name(session['user_id'], name)
        
        # Update password if provided
        if new_password:
            if not auth_manager.verify_current_password(session['user_id'], current_password):
                return jsonify({'error': 'Current password is incorrect'}), 400
            
            success = success and auth_manager.update_user_password(session['user_id'], new_password)
        
        if success:
            session['user_name'] = name
            return jsonify({'message': 'Profile updated successfully'})
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
    
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': 'Failed to update profile'}), 500

@app.route('/feedback')
@login_required
def feedback():
    return render_template('feedback.html')

@app.route('/api/submit-feedback', methods=['POST'])
@login_required
def submit_feedback():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        feedback_id = db_manager.save_user_feedback(session['user_id'], message)
        
        return jsonify({
            'feedback_id': feedback_id,
            'message': 'Feedback submitted successfully'
        })
    
    except Exception as e:
        logger.error(f"Feedback submission error: {str(e)}")
        return jsonify({'error': 'Failed to submit feedback'}), 500

@app.route('/admin')
@role_required(['admin'])
def admin_panel():
    try:
        stats = db_manager.get_admin_stats()
        return render_template('admin.html', stats=stats)
    except Exception as e:
        logger.error(f"Admin panel error: {str(e)}")
        return render_template('admin.html', stats={})

@app.route('/api/admin/users')
@role_required(['admin'])
def admin_users():
    try:
        users = db_manager.get_all_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Admin users error: {str(e)}")
        return jsonify([])

@app.route('/api/admin/feedback')
@role_required(['admin'])
def admin_feedback():
    try:
        feedback = db_manager.get_all_feedback()
        return jsonify(feedback)
    except Exception as e:
        logger.error(f"Admin feedback error: {str(e)}")
        return jsonify([])

if __name__ == '__main__':
    # Initialize database
    db_manager.init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)