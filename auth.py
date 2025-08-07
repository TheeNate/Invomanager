"""
Magic Link Authentication System
Simple email-based authentication for single shared inventory
"""
import os
import requests
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import session, request, url_for
from typing import Optional

class MagicLinkAuth:
    def __init__(self, db_manager):
        self.db = db_manager
        self.token_expiry_hours = 1  # Magic links expire in 1 hour
        
        # Load allowed emails from environment variable
        allowed_emails_str = os.environ.get('ALLOWED_EMAILS', '')
        self.allowed_emails = set(email.strip().lower() for email in allowed_emails_str.split(',') if email.strip())
        
        print(f"Allowed emails configured: {len(self.allowed_emails)} emails")
        if not self.allowed_emails:
            print("WARNING: No allowed emails configured. Set ALLOWED_EMAILS environment variable.")
        
    def is_email_allowed(self, email: str) -> bool:
        """Check if email is in the allowed list"""
        if not self.allowed_emails:
            # If no allowed emails are configured, deny access for security
            return False
        
        return email.lower() in self.allowed_emails
    
    def generate_magic_link(self, email: str) -> str:
        """Generate a magic link for the given email"""
        # Check if email is authorized
        if not self.is_email_allowed(email):
            raise ValueError("Email not authorized for access")
        
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
        """Send magic link via Resend API"""
        try:
            # Get Resend API key from environment
            resend_api_key = os.environ.get('RESEND_API_KEY')
            from_email = os.environ.get('FROM_EMAIL', 'Equipment Inventory <noreply@yourdomain.com>')
            
            print(f"Resend API key available: {bool(resend_api_key)}")
            print(f"From email: {from_email}")
            
            if not resend_api_key:
                print("ERROR: Resend API key not configured")
                return False
            
            # Email content
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #007bff; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                    .login-button {{ display: inline-block; background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🔧 Equipment Inventory Access</h2>
                    </div>
                    <div class="content">
                        <h3>Secure Login Link</h3>
                        <p>Hello,</p>
                        <p>Click the button below to securely access your Equipment Inventory System:</p>
                        
                        <p style="text-align: center;">
                            <a href="{magic_link}" class="login-button">Access Equipment Inventory</a>
                        </p>
                        
                        <p><strong>Important:</strong> This link will expire in {self.token_expiry_hours} hour(s) for security.</p>
                        
                        <p>If you didn't request this login, you can safely ignore this email.</p>
                        
                        <div class="footer">
                            <p>Equipment Inventory Management System<br>
                            Safety Equipment Tracking & Compliance</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
Equipment Inventory Login Link

Hello,

Click the link below to access the Equipment Inventory System:

{magic_link}

This link will expire in {self.token_expiry_hours} hour(s).

If you didn't request this login, you can safely ignore this email.

Best regards,
Equipment Inventory System
"""
            
            # Send email via Resend API
            print("Making request to Resend API...")
            payload = {
                'from': from_email,
                'to': [email],
                'subject': 'Equipment Inventory Login Link',
                'html': html_body,
                'text': text_body
            }
            print(f"Request payload: {payload}")
            
            try:
                response = requests.post(
                    'https://api.resend.com/emails',
                    headers={
                        'Authorization': f'Bearer {resend_api_key}',
                        'Content-Type': 'application/json'
                    },
                    json=payload,
                    timeout=30  # Add timeout
                )
                
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                print(f"Response body: {response.text}")
                
                if response.status_code == 200:
                    print(f"Magic link sent successfully to {email}")
                    return True
                else:
                    print(f"Failed to send email: {response.status_code} - {response.text}")
                    return False
                    
            except requests.exceptions.Timeout:
                print("ERROR: Request to Resend API timed out")
                return False
            except requests.exceptions.RequestException as req_e:
                print(f"ERROR: Request exception: {req_e}")
                return False
            
        except Exception as e:
            print(f"Error sending email via Resend: {e}")
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
                    
                    # Create or update user record and set session
                    user_id = self.db.create_or_update_user(email)
                    user = self.db.get_user_by_email(email)
                    
                    # Set session with role information
                    session['authenticated'] = True
                    session['user_email'] = email
                    session['user_id'] = user_id
                    session['user_role'] = user['role'] if user else 'technician'
                    
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
        return session.get('authenticated', False)
    
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

    def require_admin(self, f):
        """Decorator to require admin authentication"""
        from functools import wraps
        from flask import redirect, url_for
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                session['next_url'] = request.url
                return redirect(url_for('auth_login'))
            if session.get('user_role') != 'admin':
                # Redirect technicians to their document page
                user_id = session.get('user_id')
                if user_id:
                    return redirect(url_for('user_documents', user_id=user_id))
                return redirect(url_for('auth_login'))
            return f(*args, **kwargs)
        return decorated_function

    def require_user_or_admin(self, f):
        """Decorator to require user to access their own data or be admin"""
        from functools import wraps
        from flask import redirect, url_for
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                session['next_url'] = request.url
                return redirect(url_for('auth_login'))
            
            user_id = kwargs.get('user_id')
            session_user_id = session.get('user_id')
            user_role = session.get('user_role')
            
            # Allow access if user is admin OR accessing their own data
            if user_role == 'admin' or str(session_user_id) == str(user_id):
                return f(*args, **kwargs)
            else:
                # Redirect to their own documents page
                return redirect(url_for('user_documents', user_id=session_user_id))
        return decorated_function