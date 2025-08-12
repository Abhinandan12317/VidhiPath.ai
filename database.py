import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'database': 'vidhipath_db',
            'user': 'koot',
            'password': 'root',
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
    
    def get_connection(self):
        try:
            connection = mysql.connector.connect(**self.config)
            return connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def init_database(self):
        """Initialize database and create tables"""
        try:
            # Create database if not exists
            connection = mysql.connector.connect(
                host=self.config['host'],
                user=self.config['user'],
                password=self.config['password']
            )
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.close()
            connection.close()
            
            # Create tables
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                
                # Users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'user', 'guest') DEFAULT 'user',
                    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL
                )
                """)
                
                # Chat logs table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    chat_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """)
                
                # Documents table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    filename VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'uploaded',
                    extracted_summary TEXT,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """)
                
                # Case analysis table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS case_analysis (
                    analysis_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    inputs JSON NOT NULL,
                    results JSON NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """)
                
                # FAQ entries table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS faq_entries (
                    faq_id INT AUTO_INCREMENT PRIMARY KEY,
                    category VARCHAR(100) NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """)
                
                # User reports/feedback table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_reports (
                    report_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    message TEXT NOT NULL,
                    file_path VARCHAR(255) NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'pending',
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """)
                
                connection.commit()
                cursor.close()
                connection.close()
                
                # Insert default FAQs
                self.insert_default_faqs()
                
                logger.info("Database initialized successfully")
                
        except Error as e:
            logger.error(f"Database initialization error: {e}")
    
    def insert_default_faqs(self):
        """Insert default FAQ entries"""
        default_faqs = [
            {
                'category': 'RTI',
                'question': 'What is RTI Act?',
                'answer': 'Right to Information (RTI) Act 2005 is an Act of the Parliament of India to provide for setting out the practical regime of right to information for citizens.'
            },
            {
                'category': 'RTI',
                'question': 'How to file RTI application?',
                'answer': 'RTI application can be filed online through the RTI portal or offline by submitting a written application to the concerned Public Information Officer (PIO).'
            },
            {
                'category': 'FIR',
                'question': 'What is FIR?',
                'answer': 'First Information Report (FIR) is a written document prepared by police when they receive information about the commission of a cognizable offence.'
            },
            {
                'category': 'FIR',
                'question': 'Can police refuse to file FIR?',
                'answer': 'No, police cannot refuse to register FIR for cognizable offences. If they refuse, you can approach the Superintendent of Police or file a complaint before the Magistrate.'
            },
            {
                'category': 'Property',
                'question': 'What documents are required for property registration?',
                'answer': 'Sale deed, property card, tax receipts, NOC from society/builder, identity proof, address proof, and passport size photographs are typically required.'
            },
            {
                'category': 'Women and Child Rights',
                'question': 'What is domestic violence act?',
                'answer': 'The Protection of Women from Domestic Violence Act, 2005 provides protection to women from domestic violence and ensures their right to live in a shared household.'
            }
        ]
        
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                
                # Check if FAQs already exist
                cursor.execute("SELECT COUNT(*) FROM faq_entries")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    for faq in default_faqs:
                        cursor.execute("""
                        INSERT INTO faq_entries (category, question, answer) 
                        VALUES (%s, %s, %s)
                        """, (faq['category'], faq['question'], faq['answer']))
                    
                    connection.commit()
                    logger.info("Default FAQs inserted")
                
                cursor.close()
                connection.close()
                
        except Error as e:
            logger.error(f"Error inserting default FAQs: {e}")
    
    def save_chat_log(self, user_id, message, response):
        """Save chat log to database"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("""
                INSERT INTO chat_logs (user_id, message, response) 
                VALUES (%s, %s, %s)
                """, (user_id, message, response))
                connection.commit()
                chat_id = cursor.lastrowid
                cursor.close()
                connection.close()
                return chat_id
        except Error as e:
            logger.error(f"Error saving chat log: {e}")
            return None
    
    def get_chat_history(self, user_id, limit=50):
        """Get user's chat history"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                SELECT chat_id, message, response, timestamp 
                FROM chat_logs 
                WHERE user_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
                """, (user_id, limit))
                history = cursor.fetchall()
                cursor.close()
                connection.close()
                return history
        except Error as e:
            logger.error(f"Error fetching chat history: {e}")
            return []
    
    def save_document(self, user_id, filename, status, summary):
        """Save document information"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("""
                INSERT INTO documents (user_id, filename, status, extracted_summary) 
                VALUES (%s, %s, %s, %s)
                """, (user_id, filename, status, summary))
                connection.commit()
                doc_id = cursor.lastrowid
                cursor.close()
                connection.close()
                return doc_id
        except Error as e:
            logger.error(f"Error saving document: {e}")
            return None
    
    def get_user_documents(self, user_id):
        """Get user's documents"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                SELECT document_id, filename, status, extracted_summary, upload_time 
                FROM documents 
                WHERE user_id = %s 
                ORDER BY upload_time DESC
                """, (user_id,))
                documents = cursor.fetchall()
                cursor.close()
                connection.close()
                return documents
        except Error as e:
            logger.error(f"Error fetching user documents: {e}")
            return []
    
    def save_case_analysis(self, user_id, inputs, results):
        """Save case analysis"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("""
                INSERT INTO case_analysis (user_id, inputs, results) 
                VALUES (%s, %s, %s)
                """, (user_id, json.dumps(inputs), json.dumps(results)))
                connection.commit()
                analysis_id = cursor.lastrowid
                cursor.close()
                connection.close()
                return analysis_id
        except Error as e:
            logger.error(f"Error saving case analysis: {e}")
            return None
    
    def get_user_case_analyses(self, user_id):
        """Get user's case analyses"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                SELECT analysis_id, inputs, results, timestamp 
                FROM case_analysis 
                WHERE user_id = %s 
                ORDER BY timestamp DESC
                """, (user_id,))
                analyses = cursor.fetchall()
                
                # Parse JSON fields
                for analysis in analyses:
                    analysis['inputs'] = json.loads(analysis['inputs'])
                    analysis['results'] = json.loads(analysis['results'])
                
                cursor.close()
                connection.close()
                return analyses
        except Error as e:
            logger.error(f"Error fetching case analyses: {e}")
            return []
    
    def get_faq_categories(self):
        """Get all FAQ categories"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("SELECT DISTINCT category FROM faq_entries ORDER BY category")
                categories = [row[0] for row in cursor.fetchall()]
                cursor.close()
                connection.close()
                return categories
        except Error as e:
            logger.error(f"Error fetching FAQ categories: {e}")
            return []
    
    def get_all_faqs(self):
        """Get all FAQs"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                SELECT faq_id, category, question, answer 
                FROM faq_entries 
                ORDER BY category, question
                """)
                faqs = cursor.fetchall()
                cursor.close()
                connection.close()
                return faqs
        except Error as e:
            logger.error(f"Error fetching FAQs: {e}")
            return []
    
    def search_faqs(self, query, category=None):
        """Search FAQs"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                
                if category:
                    cursor.execute("""
                    SELECT faq_id, category, question, answer 
                    FROM faq_entries 
                    WHERE category = %s AND (question LIKE %s OR answer LIKE %s)
                    ORDER BY question
                    """, (category, f"%{query}%", f"%{query}%"))
                else:
                    cursor.execute("""
                    SELECT faq_id, category, question, answer 
                    FROM faq_entries 
                    WHERE question LIKE %s OR answer LIKE %s
                    ORDER BY category, question
                    """, (f"%{query}%", f"%{query}%"))
                
                results = cursor.fetchall()
                cursor.close()
                connection.close()
                return results
        except Error as e:
            logger.error(f"Error searching FAQs: {e}")
            return []
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                
                stats = {}
                
                # Chat count
                cursor.execute("SELECT COUNT(*) FROM chat_logs WHERE user_id = %s", (user_id,))
                stats['total_chats'] = cursor.fetchone()[0]
                
                # Document count
                cursor.execute("SELECT COUNT(*) FROM documents WHERE user_id = %s", (user_id,))
                stats['total_documents'] = cursor.fetchone()[0]
                
                # Case analysis count
                cursor.execute("SELECT COUNT(*) FROM case_analysis WHERE user_id = %s", (user_id,))
                stats['total_analyses'] = cursor.fetchone()[0]
                
                # Account creation date
                cursor.execute("SELECT creation_date FROM users WHERE user_id = %s", (user_id,))
                stats['account_created'] = cursor.fetchone()[0]
                
                cursor.close()
                connection.close()
                return stats
        except Error as e:
            logger.error(f"Error fetching user stats: {e}")
            return {}
    
    def save_user_feedback(self, user_id, message):
        """Save user feedback"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("""
                INSERT INTO user_reports (user_id, message) 
                VALUES (%s, %s)
                """, (user_id, message))
                connection.commit()
                feedback_id = cursor.lastrowid
                cursor.close()
                connection.close()
                return feedback_id
        except Error as e:
            logger.error(f"Error saving feedback: {e}")
            return None
    
    def get_admin_stats(self):
        """Get admin statistics"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor()
                
                stats = {}
                
                cursor.execute("SELECT COUNT(*) FROM users")
                stats['total_users'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM chat_logs")
                stats['total_chats'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM documents")
                stats['total_documents'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM case_analysis")
                stats['total_analyses'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM user_reports WHERE status = 'pending'")
                stats['pending_feedback'] = cursor.fetchone()[0]
                
                cursor.close()
                connection.close()
                return stats
        except Error as e:
            logger.error(f"Error fetching admin stats: {e}")
            return {}
    
    def get_all_users(self):
        """Get all users for admin"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                SELECT user_id, name, email, role, creation_date, last_login 
                FROM users 
                ORDER BY creation_date DESC
                """)
                users = cursor.fetchall()
                cursor.close()
                connection.close()
                return users
        except Error as e:
            logger.error(f"Error fetching all users: {e}")
            return []
    
    def get_all_feedback(self):
        """Get all feedback for admin"""
        try:
            connection = self.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                SELECT r.report_id, r.message, r.date, r.status, u.name, u.email 
                FROM user_reports r 
                JOIN users u ON r.user_id = u.user_id 
                ORDER BY r.date DESC
                """)
                feedback = cursor.fetchall()
                cursor.close()
                connection.close()
                return feedback
        except Error as e:
            logger.error(f"Error fetching all feedback: {e}")
            return []