import pdfplumber
import re
from datetime import datetime
import os


class HealthDataFetcher:
    def __init__(self):
        self.__last_sync = None
        self.__health_data = None

    def fetch_health_data_from_pdf(self, pdf_file_path: str):
        """
        Read PDF file and extract health values: heart_rate, weight, height, age,
        plus additional measurements including arms and thighs.
        """
        try:
            # Clean path
            pdf_file_path = pdf_file_path.strip('"').strip("'")

            if not os.path.exists(pdf_file_path):
                print(f"Error: File not found - {pdf_file_path}")
                return None

            print(f"Opening PDF: {pdf_file_path}")

            with pdfplumber.open(pdf_file_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

            if not full_text.strip():
                print("Warning: No text found in PDF. Using defaults.")
                return None

            print("PDF text extracted successfully. Searching for health data...")

            # Patterns for extraction (English & Arabic)
            heart_rate_pattern = r"(?:Heart\s*Rate|HR|Nab[ıi]z|Pulse)[\s:]*(\d+\.?\d*)"
            weight_pattern = r"(?:Weight|Kilo|A[ğg][ıi]rl[ıi]k|Weight\s*\(kg\))[\s:]*(\d+\.?\d*)"
            height_pattern = r"(?:Height|Boy|Height\s*\(cm\))[\s:]*(\d+\.?\d*)"
            age_pattern = r"(?:Age|Yaş|Age\s*\(years\)|DOB|Date of Birth)[\s:]*(\d+\.?\d*)"
            chest_pattern = r"(?:Chest|Göğüs|Chest\s*\(cm\))[\s:]*(\d+\.?\d*)"
            waist_pattern = r"(?:Waist|Bel|Waist\s*\(cm\))[\s:]*(\d+\.?\d*)"
            hips_pattern = r"(?:Hips|Kalça|Hips\s*\(cm\))[\s:]*(\d+\.?\d*)"

            # ✅ إضافة Patterns لـ Arms و Thighs
            arms_pattern = r"(?:Arms|Arm|Kol|Biceps|Bicep|Arm\s*\(cm\))[\s:]*(\d+\.?\d*)"
            thighs_pattern = r"(?:Thighs|Thigh|Uyluk|Leg|Thigh\s*\(cm\))[\s:]*(\d+\.?\d*)"

            name_pattern = r"(?:Name|İsim|Patient|Adı)[\s:]*([A-Za-zğüşıöçĞÜŞİÖÇ\s]+?)(?:\n|$)"
            date_pattern = r"(?:Date|Tarih|Report Date)[\s:]*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})"

            hr_match = re.search(heart_rate_pattern, full_text, re.IGNORECASE)
            weight_match = re.search(weight_pattern, full_text, re.IGNORECASE)
            height_match = re.search(height_pattern, full_text, re.IGNORECASE)
            age_match = re.search(age_pattern, full_text, re.IGNORECASE)
            chest_match = re.search(chest_pattern, full_text, re.IGNORECASE)
            waist_match = re.search(waist_pattern, full_text, re.IGNORECASE)
            hips_match = re.search(hips_pattern, full_text, re.IGNORECASE)

            # ✅ البحث عن Arms و Thighs
            arms_match = re.search(arms_pattern, full_text, re.IGNORECASE)
            thighs_match = re.search(thighs_pattern, full_text, re.IGNORECASE)

            name_match = re.search(name_pattern, full_text, re.IGNORECASE)
            date_match = re.search(date_pattern, full_text, re.IGNORECASE)

            self.__health_data = {
                "heart_rate": int(float(hr_match.group(1))) if hr_match else 75,
                "weight": float(weight_match.group(1)) if weight_match else 70.0,
                "height": float(height_match.group(1)) if height_match else 170.0,
                "age": int(float(age_match.group(1))) if age_match else None,
                "chest": float(chest_match.group(1)) if chest_match else None,
                "waist": float(waist_match.group(1)) if waist_match else None,
                "hips": float(hips_match.group(1)) if hips_match else None,
                "arms": float(arms_match.group(1)) if arms_match else None,  # ✅ جديد
                "thighs": float(thighs_match.group(1)) if thighs_match else None,  # ✅ جديد
                "name": name_match.group(1).strip() if name_match else None,
                "date": date_match.group(1) if date_match else None
            }

            print(f"Extracted - HR: {self.__health_data['heart_rate']}, "
                  f"Weight: {self.__health_data['weight']}, "
                  f"Height: {self.__health_data['height']}, "
                  f"Age: {self.__health_data['age']}")

            if self.__health_data['chest']:
                print(f"Chest: {self.__health_data['chest']}cm")
            if self.__health_data['waist']:
                print(f"Waist: {self.__health_data['waist']}cm")
            if self.__health_data['hips']:
                print(f"Hips: {self.__health_data['hips']}cm")
            if self.__health_data['arms']:  # ✅ جديد
                print(f"Arms: {self.__health_data['arms']}cm")
            if self.__health_data['thighs']:  # ✅ جديد
                print(f"Thighs: {self.__health_data['thighs']}cm")

            self.__last_sync = datetime.now()
            return self.__health_data

        except Exception as e:
            print(f"Error reading PDF: {e}")
            return None