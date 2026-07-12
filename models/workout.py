class Workout:
    def __init__(self, day_number: int, exercises: list, video_url: str, workout_id: str = None):
        self.__workout_id = workout_id
        self.__day_number = day_number
        self.__exercises = exercises
        self.__video_url = video_url
        self.__completed = False
        self.__completed_date = None

    def mark_complete(self):
        """Mark workout as completed."""
        self.__completed = True
        from datetime import datetime
        self.__completed_date = datetime.now()
        print(f"✅ Workout Day {self.__day_number} marked as completed.")

    def is_completed(self):
        """Check if workout is completed."""
        return self.__completed

    def get_day_number(self):
        """Get workout day number."""
        return self.__day_number

    def get_exercises(self):
        """Get list of exercises."""
        return self.__exercises

    def get_video_url(self):
        """Get video URL."""
        return self.__video_url

    def get_workout_id(self):
        """Get workout ID."""
        return self.__workout_id

    def get_completed_date(self):
        """Get completion date."""
        return self.__completed_date

    def set_exercises(self, exercises: list):
        """Update exercise list."""
        self.__exercises = exercises

    def to_dict(self):
        """Convert workout to dictionary for API response."""
        return {
            "workout_id": self.__workout_id,
            "day": self.__day_number,
            "exercises": self.__exercises,
            "video_url": self.__video_url,
            "completed": self.__completed,
            "completed_date": self.__completed_date.strftime("%Y-%m-%d %H:%M:%S") if self.__completed_date else None
        }