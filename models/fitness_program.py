from datetime import datetime


class FitnessProgram:
    def __init__(self, program_id: str, start_date: str):
        self.__program_id = program_id
        self.__start_date = start_date
        self.__workouts = []
        self.__formatted_date = self.__format_date(start_date)

    def __format_date(self, date_str: str) -> str:
        """Convert date from YYYY-MM-DD to readable format."""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d %B %Y")
        except:
            return date_str

    def add_workout(self, workout):
        """Add workout to program."""
        self.__workouts.append(workout)

    def view_plan(self):
        """Display the fitness program plan."""
        print(f"\nFitness Program: {self.__program_id}")
        print(f"Starting Date: {self.__formatted_date}")
        print("-" * 50)

        if not self.__workouts:
            print("No workouts in this program yet.")
            return

        for w in self.__workouts:
            status = "✅ Completed" if w.is_completed() else "⏳ Pending"
            print(f"\n📅 Day {w.get_day_number()} - {status}")
            print(f"   📹 Video: {w.get_video_url()}")
            print("   Exercises:")

            exercises = w.get_exercises()
            if exercises:
                for i, ex in enumerate(exercises, 1):
                    print(f"      {i}. {ex}")
            else:
                print("      No exercises listed.")

        # Show progress
        progress = self.get_progress_percentage()
        print(f"\n📊 Overall Progress: {progress:.1f}%")
        print("-" * 50)

    def get_workouts(self):
        """Get all workouts."""
        return self.__workouts

    def get_program_id(self):
        """Get program ID."""
        return self.__program_id

    def get_start_date(self):
        """Get start date."""
        return self.__start_date

    def get_formatted_date(self):
        """Get formatted start date."""
        return self.__formatted_date

    def get_completed_workouts_count(self):
        """Get number of completed workouts."""
        return sum(1 for w in self.__workouts if w.is_completed())

    def get_total_workouts_count(self):
        """Get total number of workouts."""
        return len(self.__workouts)

    def get_progress_percentage(self):
        """Get progress percentage."""
        total = self.get_total_workouts_count()
        if total == 0:
            return 0.0
        completed = self.get_completed_workouts_count()
        return (completed / total) * 100

    def get_workout_by_day(self, day_number: int):
        """Get a specific workout by day number."""
        for workout in self.__workouts:
            if workout.get_day_number() == day_number:
                return workout
        return None

    def to_dict(self):
        """Convert program to dictionary for API response."""
        return {
            "program_id": self.__program_id,
            "start_date": self.__start_date,
            "formatted_date": self.__formatted_date,
            "total_workouts": self.get_total_workouts_count(),
            "completed_workouts": self.get_completed_workouts_count(),
            "progress_percentage": self.get_progress_percentage(),
            "workouts": [w.to_dict() for w in self.__workouts]
        }

    def view_plan_by_week(self):
        """Display program organized by weeks."""
        print(f"\nFitness Program: {self.__program_id}")
        print(f"Starting Date: {self.__formatted_date}")
        print("=" * 50)

        if not self.__workouts:
            print("No workouts in this program.")
            return

        # Group workouts by week (assuming days_per_week is consistent)
        total_workouts = len(self.__workouts)
        days_per_week = 7  # Default, adjust based on program
        if total_workouts >= 4:
            days_per_week = total_workouts // 4 if total_workouts % 4 == 0 else total_workouts

        for week in range(0, total_workouts, days_per_week):
            week_num = week // days_per_week + 1
            print(f"\n📅 WEEK {week_num}")
            print("-" * 30)

            week_workouts = self.__workouts[week:week + days_per_week]
            for w in week_workouts:
                status = "✅" if w.is_completed() else "⏳"
                print(f"  Day {w.get_day_number()} - {status}")
                for ex in w.get_exercises()[:3]:  # Show first 3 exercises
                    print(f"     • {ex}")
                if len(w.get_exercises()) > 3:
                    print(f"     • ... and {len(w.get_exercises()) - 3} more")
            print()

        progress = self.get_progress_percentage()
        print(f"📊 Overall Progress: {progress:.1f}%")
        print("=" * 50)

    def to_dict_by_week(self):
        """Return program data organized by weeks for frontend."""
        workouts_dict = [w.to_dict() for w in self.__workouts]

        total = len(workouts_dict)
        days_per_week = max(1, total // 4) if total >= 4 else total

        weeks = []
        for i in range(0, total, days_per_week):
            week_workouts = workouts_dict[i:i + days_per_week]
            completed = sum(1 for w in week_workouts if w['completed'])
            weeks.append({
                "week_number": len(weeks) + 1,
                "workouts": week_workouts,
                "completed": completed,
                "total": len(week_workouts),
                "progress": round(completed / len(week_workouts) * 100, 1) if week_workouts else 0
            })

        return {
            "program_id": self.__program_id,
            "start_date": self.__start_date,
            "formatted_date": self.__formatted_date,
            "total_workouts": total,
            "completed_workouts": self.get_completed_workouts_count(),
            "progress_percentage": self.get_progress_percentage(),
            "weeks": weeks,
            "workouts": workouts_dict
        }