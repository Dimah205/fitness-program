class WorkoutHistory:
    def __init__(self):
        self.__completed_workouts = []
        self.__dates = []


    def log_workout(self, workout, date: str):
        self.__completed_workouts.append(workout)
        self.__dates.append(date)


    def view_history(self):
        print("Workout History:")
        for i, workout in enumerate(self.__completed_workouts):
            print(f"Workout Day {workout.get_day_number()} on {self.__dates[i]}")