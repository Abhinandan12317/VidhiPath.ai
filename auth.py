from werkzeug.security import generate_password_hash, check_password_hash
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            connection = self.db.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT user_id, name, email, role FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                cursor.close()
                connection.close()
                return user
        except Exception as e:
            logger.error(f"Get user by email error: {e}")
            return None

    def update_user_password_by_email(self, email, new_password):
        """Update user password by email"""
        try:
            connection = self.db.get_connection()
            if connection:
                cursor = connection.cursor()
                password_hash = generate_password_hash(new_password)
                cursor.execute("""
                UPDATE users SET password_hash = %s WHERE email = %s
                """, (password_hash, email))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Exception as e:
            logger.error(f"Update password by email error: {e}")
            return False
    
    def register_user(self, name, email, password, role='user'):
        """Register a new user"""
        try:
            connection = self.db.get_connection()
            if connection:
                cursor = connection.cursor()
                
                # Check if email already exists
                cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    cursor.close()
                    connection.close()
                    return False
                
                # Create password hash
                password_hash = generate_password_hash(password)
                
                # Insert new user
                cursor.execute("""
                INSERT INTO users (name, email, password_hash, role) 
                VALUES (%s, %s, %s, %s)
                """, (name, email, password_hash, role))
                
                connection.commit()
                cursor.close()
                connection.close()
                return True
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False
    
    def authenticate_user(self, email, password):
        """Authenticate user login"""
        try:
            connection = self.db.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                
                # Get user by email
                cursor.execute("""
                SELECT user_id, name, email, password_hash, role 
                FROM users WHERE email = %s
                """, (email,))
                
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password_hash'], password):
                    # Update last login
                    cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE user_id = %s
                    """, (user['user_id'],))
                    connection.commit()
                    
                    cursor.close()
                    connection.close()
                    return user
                
                cursor.close()
                connection.close()
                return None
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            connection = self.db.get_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                
                cursor.execute("""
                SELECT user_id, name, email, role, creation_date, last_login 
                FROM users WHERE user_id = %s
                """, (user_id,))
                
                user = cursor.fetchone()
                cursor.close()
                connection.close()
                return user
                
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None
    
    def update_user_name(self, user_id, name):
        """Update user name"""
        try:
            connection = self.db.get_connection()
            if connection:
                cursor = connection.cursor()
                
                cursor.execute("""
                UPDATE users SET name = %s WHERE user_id = %s
                """, (name, user_id))
                
                connection.commit()
                cursor.close()
                connection.close()
                return True
                
        except Exception as e:
            logger.error(f"Update name error: {e}")
            return False
    
    def verify_current_password(self, user_id, password):
        """Verify current password"""
        try:
            connection = self.db.get_connection()
            if connection:
                cursor = connection.cursor()
                
                cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                
                cursor.close()
                connection.close()
                
                if result:
                    return check_password_hash(result[0], password)
                return False
                
        except Exception as e:
            logger.error(f"Verify password error: {e}")
            return False
    
    def update_user_password(self, user_id, new_password):
        """Update user password"""
        try:
            connection = self.db.get_connection()
            if connection:
                cursor = connection.cursor()
                
                password_hash = generate_password_hash(new_password)
                cursor.execute("""
                UPDATE users SET password_hash = %s WHERE user_id = %s
                """, (password_hash, user_id))
                
                connection.commit()
                cursor.close()
                connection.close()
                return True
                
        except Exception as e:
            logger.error(f"Update password error: {e}")
            return False