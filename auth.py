"""
Magic Link Authentication System
Simple email-based authentication for single shared inventory
"""
import os
import smtplib
import secrets
import hashlib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import session, request, url_for
from typing import Optional

class MagicLinkAuth:
    def __init__(self, db_manager):
        self.db = db_manager
        self.token_expiry_hours = 1  # Magic links expire in 1 hour
        
    def generate_magic_link(self, email: str) -> str:
        """Generate a magic link for the given email"""
        # Generate secure token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Store token in database with expiry
        expiry_time = datetime.now() + timedelta(hours=self.token_expiry_hours)
        
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                
                # Create auth_tokens table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_tokens (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) NOT NULL,
                        token_hash VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        used BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Clean up expired tokens
                cursor.execute("DELETE FROM auth_tokens WHERE expires_at < NOW()")
                
                # Insert new token
                cursor.execute(
                    "INSERT INTO auth_tokens (email, token_hash, expires_at) VALUES (%s, %s, %s)",
                    (email, token_hash, expiry_time)
                )
                conn.commit()
                
        except Exception as e:
            print(f"Database error generating magic link: {e}")
            raise
            
        # Generate the magic link URL
        magic_link = url_for('auth_verify', token=token, _external=True)
        return magic_link
    
    def send_magic_link(self, email: str, magic_link: str) -> bool:
        """Send magic link via email"""
        try:
            # Email configuration from environment variables
            smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.environ.get('SMTP_PORT', '587'))
            smtp_username = os.environ.get('SMTP_USERNAME')
            smtp_password = os.environ.get('SMTP_PASSWORD')
            from_email = os.environ.get('FROM_EMAIL', smtp_username)
            
            if not smtp_username or not smtp_password:
                print("SMTP credentials not configured")
                return False
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = email
            msg['Subject'] = "Equipment Inventory Login Link"
            
            # Email body
            body = f"""
Hello,

Click the link below to access the Equipment Inventory System:

{magic_link}

This link will expire in {self.token_expiry_hours} hour(s).

If you didn't request this login, you can safely ignore this email.

Best regards,
Equipment Inventory System
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            text = msg.as_string()
            server.sendmail(from_email, email, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def verify_magic_link(self, token: str) -> Optional[str]:
        """Verify magic link token and return email if valid"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                
                # Find valid, unused token
                cursor.execute("""
                    SELECT email FROM auth_tokens 
                    WHERE token_hash = %s 
                    AND expires_at > NOW() 
                    AND used = FALSE
                """, (token_hash,))
                
                result = cursor.fetchone()
                
                if result:
                    email = result[0]
                    
                    # Mark token as used
                    cursor.execute(
                        "UPDATE auth_tokens SET used = TRUE WHERE token_hash = %s",
                        (token_hash,)
                    )
                    conn.commit()
                    
                    return email
                    
        except Exception as e:
            print(f"Database error verifying token: {e}")
            
        return None
    
    def login_user(self, email: str):
        """Log in user by storing email in session"""
        session['user_email'] = email
        session['logged_in'] = True
        session['login_time'] = datetime.now().isoformat()
    
    def logout_user(self):
        """Log out user by clearing session"""
        session.clear()
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return session.get('logged_in', False)
    
    def get_current_user(self) -> Optional[str]:
        """Get current user's email"""
        if self.is_authenticated():
            return session.get('user_email')
        return None
    
    def require_auth(self, f):
        """Decorator to require authentication for routes"""
        from functools import wraps
        from flask import redirect, url_for
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                # Store the URL they were trying to access
                session['next_url'] = request.url
                return redirect(url_for('auth_login'))
            return f(*args, **kwargs)
        return decorated_function