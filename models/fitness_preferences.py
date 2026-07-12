class FitnessPreferences:
    def __init__(self, fitness_goal: str, workout_days: int, program_duration: str = "monthly"):
        self.__fitness_goal = fitness_goal
        self.__workout_days = workout_days  # Days per week
        self.__program_duration = program_duration  # "weekly" or "monthly"
        self.__total_weeks = 4 if program_duration == "monthly" else 1
        self.__total_days = self.__total_weeks * workout_days

    def set_preferences(self, goal: str, days: int, duration: str = "monthly"):
        self.__fitness_goal = goal
        self.__workout_days = days
        self.__program_duration = duration
        self.__total_weeks = 4 if duration == "monthly" else 1
        self.__total_days = self.__total_weeks * workout_days

    def get_preferences(self):
        return {
            "goal": self.__fitness_goal,
            "days": self.__workout_days,  # Days per week
            "duration": self.__program_duration,
            "total_weeks": self.__total_weeks,
            "total_days": self.__total_days
        }