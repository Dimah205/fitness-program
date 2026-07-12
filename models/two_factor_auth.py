import random
from datetime import datetime, timedelta
from models.email_service import EmailService


class TwoFactorAuth:
    """
    Two-Factor Authentication using Email verification.
    Sends a 6-digit code to user's email address.
    """

    def __init__(self, email: str):
        self.__email = email
        self.__verification_code = None
        self.__code_expiry = None
        self.__email_service = EmailService()

    def generate_code(self) -> str:
        """Generate a 6-digit verification code."""
        self.__verification_code = self.__email_service.generate_code()
        self.__code_expiry = datetime.now() + timedelta(minutes=2)
        return self.__verification_code

    def send_code(self) -> bool:
        """
        Generate and send verification code to user's email.
        Returns True if email sent successfully.
        """
        code = self.generate_code()
        return self.__email_service.send_verification_email(self.__email, code)

    def verify_code(self, code: str) -> bool:
        """
        Verify the provided code.
        Returns True if code is valid and not expired.
        """
        if datetime.now() > self.__code_expiry:
            print("❌ Verification code expired.")
            return False

        if code == self.__verification_code:
            print("✅ Verification successful.")
            return True

        print("❌ Invalid verification code.")
        return False