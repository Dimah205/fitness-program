from models.email_service import EmailService
from models.workout_history import WorkoutHistory
from utils.password_utils import hash_password, check_password
from database.db_manager import create_user, get_user_by_email, generate_short_id
from datetime import datetime, timedelta


class User:
    def __init__(self, phone_number: str, email: str, password: str, user_id: str = None):
        # Generate short 5-character ID (e.g., U123, UABC)
        self.__user_id = user_id if user_id else generate_short_id('U')
        self.__phone_number = phone_number
        self.__email = email
        self.__password_hash = hash_password(password) if password else None
        self.__workout_history = WorkoutHistory()
        self.__fitness_program = None

        # Email verification for registration
        self.__email_service = EmailService()
        self.__verification_code = None
        self.__code_expiry = None
        self.__email_verified = False

    def register(self):
        """Register a new user - sends verification email."""
        existing_user = get_user_by_email(self.__email)
        if existing_user:
            print(f"❌ Email {self.__email} is already registered.")
            return "exists"

        self.__verification_code = self.__email_service.generate_code()
        self.__code_expiry = datetime.now() + timedelta(minutes=5)
        self.__email_service.send_verification_email(self.__email, self.__verification_code)

        print(f"✅ Verification code sent to {self.__email}")
        return "verification_sent"

    def verify_email_and_create(self, code: str) -> bool:
        """Verify email and create user."""
        if datetime.now() > self.__code_expiry:
            print("❌ Verification code expired.")
            return False

        if code != self.__verification_code:
            print("❌ Invalid verification code.")
            return False

        create_user(self.__user_id, self.__phone_number, self.__email, self.__password_hash)
        self.__email_verified = True
        print(f"✅ User created with ID: {self.__user_id}")
        return True

    def login(self, password_attempt: str) -> bool:
        """Login with email and password only."""
        user_data = get_user_by_email(self.__email)
        if not user_data:
            print("❌ Email not found.")
            return False

        if check_password(password_attempt, user_data['password_hash']):
            self.__user_id = user_data['user_id']
            self.__phone_number = user_data['phone_number']
            print(f"✅ Login successful! User ID: {self.__user_id}")
            return True

        print("❌ Incorrect password.")
        return False

    def get_user_id(self):
        return self.__user_id

    def get_email(self):
        return self.__email

    def get_phone_number(self):
        return self.__phone_number

    def set_fitness_program(self, program):
        self.__fitness_program = program

    def get_fitness_program(self):
        return self.__fitness_program

    def get_workout_history(self):
        return self.__workout_history