import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    """
    Email service for sending verification codes.
    Supports both Gmail SMTP and SendGrid API.
    """

    def __init__(self):
        self.provider = os.getenv('EMAIL_PROVIDER', 'smtp')  # 'smtp' or 'sendgrid'
        self.app_name = os.getenv('APP_NAME', 'Fitness AI')

        # Gmail SMTP settings
        self.smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 587))
        self.sender_email = os.getenv('EMAIL_SENDER', 'your_email@gmail.com')
        self.sender_password = os.getenv('EMAIL_PASSWORD', '')

        # SendGrid settings
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY', '')

        self.__verification_codes = {}

    def generate_code(self) -> str:
        """Generate a 6-digit verification code."""
        return str(random.randint(100000, 999999))

    def send_verification_email(self, to_email: str, code: str) -> bool:
        """Send verification code to user's email."""

        # Try SendGrid first if configured
        if self.provider == 'sendgrid' and self.sendgrid_api_key:
            return self._send_via_sendgrid(to_email, code)

        # Fallback to SMTP (Gmail)
        if self.provider == 'smtp' and self.sender_password:
            return self._send_via_smtp(to_email, code)

        # Mock mode if no credentials
        print("\n⚠️ Email credentials not configured. Using MOCK mode.")
        print(f"\n[MOCK EMAIL] To: {to_email}")
        print(f"[MOCK EMAIL] Verification code: {code}\n")
        return True

    def _send_via_smtp(self, to_email: str, code: str) -> bool:
        """Send email via SMTP (Gmail)."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'🔐 {self.app_name} - Verification Code'
            msg['From'] = f'"{self.app_name}" <{self.sender_email}>'
            msg['To'] = to_email

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0;">
                    <h1 style="margin: 0;">🏋️ {self.app_name}</h1>
                </div>
                <div style="background: white; padding: 40px 30px; text-align: center; border-radius: 0 0 12px 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <h2>Verify Your Identity</h2>
                    <p>Your verification code is:</p>
                    <div style="font-size: 48px; font-weight: bold; letter-spacing: 8px; color: #667eea; background: #f0f0f0; padding: 15px; border-radius: 8px; margin: 20px 0;">{code}</div>
                    <p style="color: #888;">⏰ This code expires in 2 minutes.</p>
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            print(f"✅ Verification email sent to {to_email}")
            return True

        except Exception as e:
            print(f"❌ SMTP failed: {e}")
            print(f"\n[MOCK] Verification code: {code}\n")
            return True

    def _send_via_sendgrid(self, to_email: str, code: str) -> bool:
        """Send email via SendGrid API."""
        try:
            import requests

            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": self.sender_email, "name": self.app_name},
                "subject": f"🔐 {self.app_name} - Verification Code",
                "content": [{
                    "type": "text/html",
                    "value": f"""
                    <h1>Your verification code is: <strong>{code}</strong></h1>
                    <p>This code expires in 2 minutes.</p>
                    """
                }]
            }

            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 202:
                print(f"✅ Verification email sent to {to_email} via SendGrid")
                return True
            else:
                raise Exception(f"SendGrid error: {response.text}")

        except Exception as e:
            print(f"❌ SendGrid failed: {e}")
            print(f"\n[MOCK] Verification code: {code}\n")
            return True