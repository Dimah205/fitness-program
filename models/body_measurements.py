"""
Body Measurements Tracking Module
Tracks user weight and body measurements over time.
"""

from datetime import datetime


class BodyMeasurement:
    """Single body measurement record."""

    def __init__(self, measurement_id: str, user_id: str, weight: float,
                 chest: float = None, waist: float = None, hips: float = None,
                 arms: float = None, thighs: float = None, notes: str = None,
                 recorded_date: str = None):
        self.__measurement_id = measurement_id
        self.__user_id = user_id
        self.__weight = weight
        self.__chest = chest
        self.__waist = waist
        self.__hips = hips
        self.__arms = arms
        self.__thighs = thighs
        self.__notes = notes
        self.__recorded_date = recorded_date or datetime.now().strftime("%Y-%m-%d")

    def get_weight(self):
        return self.__weight

    def get_all_measurements(self):
        return {
            "weight": self.__weight,
            "chest": self.__chest,
            "waist": self.__waist,
            "hips": self.__hips,
            "arms": self.__arms,
            "thighs": self.__thighs,
            "notes": self.__notes,
            "date": self.__recorded_date,
            "id": self.__measurement_id
        }


class BodyTracker:
    """Tracks and analyzes body measurements over time."""

    def __init__(self):
        pass

    def calculate_bmi(self, weight: float, height_cm: float) -> dict:
        """
        Calculate BMI (Body Mass Index).
        Formula: weight(kg) / (height(m))^2
        """
        height_m = height_cm / 100
        bmi = weight / (height_m ** 2)

        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal Weight"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"

        return {
            "bmi": round(bmi, 1),
            "category": category
        }

    def calculate_weight_change(self, current: float, previous: float) -> dict:
        """Calculate weight change between two measurements."""
        change = current - previous
        direction = "gained" if change > 0 else "lost" if change < 0 else "maintained"

        return {
            "change": round(change, 2),
            "direction": direction,
            "absolute_change": abs(round(change, 2))
        }

    def get_progress_summary(self, measurements: list, height_cm: float) -> dict:
        """
        Generate a summary of progress from measurement history.
        """
        if not measurements or len(measurements) < 1:
            return {"error": "Not enough data"}

        first = measurements[0]
        latest = measurements[-1]

        weight_change = self.calculate_weight_change(
            float(latest['weight']), float(first['weight'])
        )

        bmi_data = self.calculate_bmi(float(latest['weight']), height_cm)

        # Calculate days tracked safely
        try:
            from datetime import datetime, date

            def to_date(d):
                if isinstance(d, str):
                    return datetime.strptime(d, "%Y-%m-%d").date()
                elif isinstance(d, datetime):
                    return d.date()
                elif isinstance(d, date):
                    return d
                return datetime.now().date()

            d1 = to_date(first['recorded_date'])
            d2 = to_date(latest['recorded_date'])
            days_tracked = (d2 - d1).days
        except:
            days_tracked = 0

        # Calculate trends
        waist_change = None
        if first.get('waist') and latest.get('waist'):
            waist_change = round(float(latest['waist']) - float(first['waist']), 2)

        return {
            "total_measurements": len(measurements),
            "first_date": str(first['recorded_date']),
            "latest_date": str(latest['recorded_date']),
            "days_tracked": days_tracked,
            "weight": {
                "start": float(first['weight']),
                "current": float(latest['weight']),
                "change": weight_change
            },
            "bmi": bmi_data,
            "waist_change": waist_change,
            "trend": "improving" if weight_change['direction'] == 'lost' else "stable"
        }