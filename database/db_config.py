import os
from dotenv import load_dotenv

load_dotenv()

config = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'fitness'),
    'raise_on_warnings': True
}