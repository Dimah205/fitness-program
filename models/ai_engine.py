from models.fitness_program import FitnessProgram
from models.workout import Workout
from database.db_manager import (
    save_fitness_program, save_workout, save_exercise,
    delete_user_program, get_user_program, generate_short_id,
    get_workouts_by_program, get_exercises_by_workout,
    mark_workout_completed, save_workout_history,
    get_program_progress, get_workout_by_id, get_program_by_workout
)
from datetime import datetime
import random
import re


class AIEngine:

    def generate_and_save_program(self, user_id: str, preferences, health_data=None, pref_id=None, sync_id=None):
        """Generate a MONTHLY program (4 weeks) and save to database."""
        import random

        existing_program = get_user_program(user_id)
        if existing_program:
            print(f"🗑️ Deleting old program for user {user_id}")
            delete_user_program(user_id)

        pref_data = preferences.get_preferences()
        goal = pref_data["goal"].lower()
        days_per_week = pref_data["days"]
        total_weeks = pref_data.get("total_weeks", 4)

        program_id = generate_short_id('P')
        start_date = datetime.now().strftime("%Y-%m-%d")

        program = FitnessProgram(program_id, start_date)

        # Generate workouts for 4 weeks
        day_counter = 1
        for week in range(1, total_weeks + 1):
            intensity = 1 + (week - 1) * 0.2

            for day in range(1, days_per_week + 1):
                # ✅ IMPORTANT: Set different random seed for EACH day
                # This ensures exercises are different every single day
                random.seed(day_counter * 100 + week * 10 + hash(goal) % 1000)

                exercises = self.__build_exercises_weekly(goal, day, week, health_data or {}, intensity)
                video_url = self.__get_video_url(goal)
                workout = Workout(day_counter, exercises, video_url)
                program.add_workout(workout)
                day_counter += 1

        random.seed()  # Reset random seed

        # Save program
        save_fitness_program(program_id, user_id, start_date, pref_id, sync_id)
        print(f"✅ Monthly Program {program_id} saved ({day_counter - 1} days over {total_weeks} weeks)")

        # Save workouts and exercises
        for workout in program.get_workouts():
            workout_id = generate_short_id('W')
            save_workout(workout_id, program_id, workout.get_day_number(),
                         self.__get_video_url(goal))

            for idx, exercise in enumerate(workout.get_exercises()):
                save_exercise(workout_id, exercise, "", idx)

        print(f"✅ {day_counter - 1} unique workouts saved with exercises.")
        return program

    def __get_video_url(self, goal: str) -> str:
        if "loss" in goal or "fat" in goal:
            return "https://www.youtube.com/watch?v=ml6cT4AZdqI"
        elif "gain" in goal or "muscle" in goal:
            return "https://www.youtube.com/watch?v=UItWltVZZmE"
        else:
            return "https://www.youtube.com/watch?v=3sE3OgU5vKM"

    def __build_exercises(self, goal, day, health_data):
        """Enhanced exercise builder with more variety and intelligence."""

        # All 50 exercises database
        EXERCISES_DB = {
            "legs": ["Squats", "Lunges", "Deadlift", "Leg Press", "Leg Extensions", "Leg Curls",
                     "Calf Raises", "Hip Thrust", "Glute Bridge", "Bulgarian Split Squats",
                     "Step-ups", "Wall Sit"],
            "chest": ["Push-ups", "Bench Press", "Incline Bench Press", "Decline Bench Press", "Chest Fly"],
            "back": ["Pull-ups", "Chin-ups", "Lat Pulldown", "Seated Row", "Bent-over Row",
                     "Dumbbell Rows", "Cable Rows", "Superman Exercise", "Back Extensions"],
            "shoulders": ["Shoulder Press", "Lateral Raises", "Front Raises", "Shoulder Shrugs"],
            "arms": ["Bicep Curls", "Tricep Dips", "Tricep Pushdown", "Skull Crushers", "Hammer Curls"],
            "core": ["Plank", "Sit-ups", "Crunches", "Russian Twists", "Bicycle Crunches",
                     "Leg Raises", "Hanging Leg Raises", "Side Plank"],
            "cardio": ["Mountain Climbers", "Jumping Jacks", "Burpees", "High Knees",
                       "Butt Kicks", "Jump Rope", "Kettlebell Swings"]
        }

        warmup_options = ["🚶 Walking (5 min)", "🔄 Arm Circles (2 min)", "🦵 Leg Swings (2 min each leg)",
                          "🤸 Jumping Jacks (3 min)"]
        warmup = [random.choice(warmup_options)]

        heart_rate = health_data.get("heart_rate") if health_data else None
        weight = health_data.get("weight") if health_data else None
        height = health_data.get("height") if health_data else None

        # Calculate BMI
        bmi = None
        if weight and height:
            height_m = height / 100
            bmi = weight / (height_m ** 2)

        if heart_rate and heart_rate > 100:
            return warmup + ["🧘 Deep Breathing (5 min)", "🚶 Slow Walking (10 min)", "🧘 Gentle Stretching (10 min)"]

        import random

        if "gain" in goal or "muscle" in goal:
            muscle_groups = list(EXERCISES_DB.keys())[:5]  # legs, chest, back, shoulders, arms
            group = muscle_groups[(day - 1) % len(muscle_groups)]
            strength = [f"💪 {random.choice(EXERCISES_DB[group])} (3 sets x 12 reps)"]

            other_group = muscle_groups[(day) % len(muscle_groups)]
            strength.append(f"💪 {random.choice(EXERCISES_DB[other_group])} (3 sets x 10 reps)")

            if day % 2 == 0:
                extra_group = muscle_groups[(day + 1) % len(muscle_groups)]
                strength.append(f"💪 {random.choice(EXERCISES_DB[extra_group])} (3 sets x 10 reps)")

        elif "loss" in goal or "fat" in goal:
            cardio_exercises = EXERCISES_DB["cardio"]
            selected = random.sample(cardio_exercises, min(3, len(cardio_exercises)))
            strength_ex = random.sample(EXERCISES_DB["legs"][:3] + EXERCISES_DB["core"][:3], 2)

            cardio = [f"🔥 {ex} (40 sec ON / 20 sec OFF x 3 rounds)" for ex in selected]
            strength = [f"💪 {ex} (3 sets x 15 reps)" for ex in strength_ex]

            return warmup + cardio + strength + ["🧘 Cool-down Stretch (5 min)"]

        else:
            all_ex = (EXERCISES_DB["legs"][:2] + EXERCISES_DB["chest"][:1] +
                      EXERCISES_DB["core"][:3] + EXERCISES_DB["cardio"][:2])
            selected = random.sample(all_ex, min(5, len(all_ex)))
            exercises = [f"💪 {ex} (3 sets x 12 reps)" for ex in selected]

            return warmup + exercises + ["🧘 Full Body Stretch (5 min)"]

        cooldown = ["🧘 Full Body Stretch (5 min)"]
        return warmup + strength + cooldown

    def load_program_from_database(self, user_id: str):
        """Load user's program from database."""
        program_data = get_user_program(user_id)
        if not program_data:
            print(f"❌ No program found for user {user_id}")
            return None

        program = FitnessProgram(
            program_data['program_id'],
            str(program_data['start_date'])
        )

        workouts = get_workouts_by_program(program_data['program_id'])

        for workout_data in workouts:
            exercises_data = get_exercises_by_workout(workout_data['workout_id'])
            exercises = [ex['exercise_name'] for ex in exercises_data]

            workout = Workout(
                workout_data['day_number'],
                exercises,
                workout_data['video_url']
            )

            if workout_data['completed']:
                workout.mark_complete()

            program.add_workout(workout)

        print(f"✅ Program {program_data['program_id']} loaded.")
        return program

    def complete_workout(self, user_id: str, workout_id: str) -> dict:
        """
        Mark a workout as completed and save to history.
        Returns updated progress information.
        """
        # Get workout details
        workout_data = get_workout_by_id(workout_id)
        if not workout_data:
            return {"success": False, "message": "Workout not found"}

        if workout_data['completed']:
            return {"success": False, "message": "Workout already completed"}

        # Mark as completed
        completed_date = datetime.now()
        mark_workout_completed(workout_id, completed_date)

        # Save to history
        save_workout_history(user_id, workout_id, completed_date)

        # Get updated progress
        progress = get_program_progress(workout_data['program_id'])

        # Get next workout (if any)
        next_workout = self.__get_next_incomplete_workout(workout_data['program_id'])

        print(f"✅ Workout {workout_id} completed! Progress: {progress['percentage']}%")

        return {
            "success": True,
            "message": f"Workout day {workout_data['day_number']} completed!",
            "day_completed": workout_data['day_number'],
            "progress": progress,
            "next_workout": next_workout
        }

    def __get_next_incomplete_workout(self, program_id: str) -> dict:
        """Get the next incomplete workout in the program."""
        workouts = get_workouts_by_program(program_id)
        for workout in workouts:
            if not workout['completed']:
                return {
                    "workout_id": workout['workout_id'],
                    "day": workout['day_number']
                }
        return None  # All workouts completed

    def get_program_with_progress(self, user_id: str) -> dict:
        """
        Get user's program with detailed progress information organized by weeks.
        """
        from database.db_manager import get_user_program, get_workouts_by_program, get_exercises_by_workout

        program_data = get_user_program(user_id)
        if not program_data:
            return None

        program = self.load_program_from_database(user_id)
        if not program:
            return None

        progress = get_program_progress(program_data['program_id'])
        next_workout = self.__get_next_incomplete_workout(program_data['program_id'])

        # Get preferences to know days_per_week
        from database.db_manager import get_preferences_by_user
        prefs = get_preferences_by_user(user_id)
        days_per_week = prefs['workout_days'] if prefs else 4

        # Get all workouts
        workouts_data = get_workouts_by_program(program_data['program_id'])

        # Build workouts list with exercises
        all_workouts = []
        for w in workouts_data:
            exercises_data = get_exercises_by_workout(w['workout_id'])
            exercises = [ex['exercise_name'] for ex in exercises_data]
            all_workouts.append({
                "workout_id": w['workout_id'],
                "day": w['day_number'],
                "completed": bool(w['completed']),
                "completed_date": str(w['completed_date']) if w['completed_date'] else None,
                "video_url": w['video_url'],
                "exercises": exercises
            })

        # Group workouts by week
        weeks = []
        total_workouts = len(all_workouts)
        workouts_per_week = days_per_week

        for i in range(0, total_workouts, workouts_per_week):
            week_workouts = all_workouts[i:i + workouts_per_week]
            week_number = i // workouts_per_week + 1
            completed_count = sum(1 for w in week_workouts if w['completed'])

            weeks.append({
                "week_number": week_number,
                "workouts": week_workouts,
                "completed": completed_count,
                "total": len(week_workouts),
                "progress": round((completed_count / len(week_workouts)) * 100, 1) if week_workouts else 0
            })

        # Build program dict with weeks
        program_dict = program.to_dict()
        program_dict["weeks"] = weeks
        program_dict["workouts"] = all_workouts

        return {
            "program": program_dict,
            "progress": progress,
            "next_workout": next_workout,
            "all_completed": progress['completed'] == progress['total']
        }

    def __build_exercises_weekly(self, goal, day, week, health_data, intensity=1.0):
        """
        Build exercises with progressive overload based on week number.
        Week 1: Beginner | Week 2: Intermediate | Week 3: Advanced | Week 4: Expert
        """
        import random

        warmup = ["🚶 Warm-up (5 min walking)"]
        heart_rate = health_data.get("heart_rate") if health_data else None

        if heart_rate and heart_rate > 100:
            return warmup + ["🧘 Light Stretching", "🚶 Slow Walking (10 min)", "🌬️ Deep Breathing"]

        # Calculate reps based on intensity
        base_reps = 10
        reps = int(base_reps * intensity)
        sets = min(3 + week - 1, 5)

        week_label = f"[W{week}]"

        # All 50 exercises database
        EXERCISES_DB = {
            "legs": [
                "🏋️ Squats", "🏋️ Lunges", "🏋️ Deadlift", "🏋️ Leg Press",
                "🏋️ Leg Extensions", "🏋️ Leg Curls", "🏋️ Calf Raises",
                "🏋️ Hip Thrust", "🏋️ Glute Bridge", "🏋️ Bulgarian Split Squats",
                "🏋️ Step-ups", "🏋️ Wall Sit"
            ],
            "chest": [
                "💪 Push-ups", "💪 Bench Press", "💪 Incline Bench Press",
                "💪 Decline Bench Press", "💪 Chest Fly"
            ],
            "back": [
                "🏋️ Pull-ups", "🏋️ Chin-ups", "🏋️ Lat Pulldown",
                "🏋️ Seated Row", "🏋️ Bent-over Row", "🏋️ Dumbbell Rows",
                "🏋️ Cable Rows", "🏋️ Superman Exercise", "🏋️ Back Extensions"
            ],
            "shoulders": [
                "🏋️ Shoulder Press", "🏋️ Lateral Raises", "🏋️ Front Raises", "🏋️ Shoulder Shrugs"
            ],
            "arms": [
                "💪 Bicep Curls", "💪 Tricep Dips", "💪 Tricep Pushdown",
                "💪 Skull Crushers", "💪 Hammer Curls"
            ],
            "core": [
                "🧘 Plank", "🧘 Sit-ups", "🧘 Crunches", "🧘 Russian Twists",
                "🧘 Bicycle Crunches", "🧘 Leg Raises", "🧘 Hanging Leg Raises",
                "🧘 Side Plank"
            ],
            "cardio": [
                "🏃 Mountain Climbers", "🏃 Jumping Jacks", "🏃 Burpees",
                "🏃 High Knees", "🏃 Butt Kicks", "🏃 Jump Rope", "🏃 Kettlebell Swings"
            ]
        }

        # ========== MUSCLE GAIN ==========
        if "gain" in goal or "muscle" in goal:
            # Use day and week to create unique seed for randomness
            random.seed(day * 100 + week * 10 + int(goal == "muscle"))

            muscle_days = ["legs", "chest", "back", "shoulders", "arms", "legs", "core"]
            focus = muscle_days[(day - 1) % len(muscle_days)]

            exercises = []

            # Main muscle group (3 exercises)
            main_exercises = random.sample(EXERCISES_DB[focus], min(3, len(EXERCISES_DB[focus])))
            for ex in main_exercises:
                exercises.append(f"{ex} ({sets} sets x {reps} reps)")

            # Secondary muscle group (2 exercises) - different from main
            available_groups = [g for g in EXERCISES_DB.keys() if g != focus and g != "cardio"]
            secondary = random.choice(available_groups)
            secondary_exercises = random.sample(EXERCISES_DB[secondary], min(2, len(EXERCISES_DB[secondary])))
            for ex in secondary_exercises:
                exercises.append(f"{ex} ({sets} sets x {reps} reps)")

            # Core every other day
            if day % 2 == 0:
                core_ex = random.choice(EXERCISES_DB["core"])
                exercises.append(f"{core_ex} ({sets} sets x {reps + 5} sec)")

        # ========== WEIGHT LOSS ==========
        elif "loss" in goal or "fat" in goal:
            random.seed(day * 50 + week * 20)

            exercises = []

            # Cardio exercises (3-4 exercises) - different each day
            cardio_random = random.sample(EXERCISES_DB["cardio"], min(4, len(EXERCISES_DB["cardio"])))
            for i, ex in enumerate(cardio_random):
                duration = 30 + (week * 5) + (i * 5)
                exercises.append(f"{ex} ({duration} sec ON / 15 sec OFF x 3 rounds)")

            # Compound exercises (2 exercises)
            compound = EXERCISES_DB["legs"][:4] + EXERCISES_DB["chest"][:2] + EXERCISES_DB["back"][:3]
            compound_ex = random.sample(compound, min(2, len(compound)))
            for ex in compound_ex:
                exercises.append(f"{ex} ({sets + 1} sets x {reps + 5} reps)")

            # Core finisher
            core_ex = random.choice(EXERCISES_DB["core"])
            exercises.append(f"{core_ex} (45 sec hold x 3 rounds)")

        # ========== GENERAL FITNESS ==========
        else:
            random.seed(day * 30 + week * 15 + 100)

            exercises = []

            # Pick 1 exercise from each category (balanced full body)
            categories = ["legs", "chest", "back", "shoulders", "core", "cardio"]

            for cat in categories:
                ex = random.choice(EXERCISES_DB[cat])
                if cat == "cardio":
                    exercises.append(f"{ex} (45 sec ON / 15 sec OFF x 3 rounds)")
                elif cat == "core":
                    exercises.append(f"{ex} (3 sets x 45 sec hold)")
                else:
                    exercises.append(f"{ex} ({sets} sets x {reps} reps)")

            # Add one arm exercise every other day
            if day % 2 == 0:
                arm_ex = random.choice(EXERCISES_DB["arms"])
                exercises.append(f"{arm_ex} ({sets} sets x {reps} reps per arm)")

        # Reset random seed
        random.seed()

        return warmup + exercises + ["🧘 Cool-down Stretching (5 min)"]

    def get_exercise_details(self, exercise_string: str) -> dict:
        """
        Extract detailed information from exercise string.
        Example: "💪 Push-ups (3 sets x 12 reps)" -> {"name": "Push-ups", "sets": 3, "reps": 12, "emoji": "💪"}
        """
        # Extract emoji
        emoji_match = re.match(r'^([^\w\s]+)', exercise_string)
        emoji = emoji_match.group(1) if emoji_match else "💪"

        # Remove emoji from string
        clean_string = re.sub(r'^[^\w\s]+', '', exercise_string).strip()

        # Extract sets and reps
        sets_reps_match = re.search(r'\((\d+)\s*[x×]\s*(\d+)', clean_string)
        if sets_reps_match:
            sets = int(sets_reps_match.group(1))
            reps = int(sets_reps_match.group(2))
            name = re.sub(r'\s*\([^)]*\)', '', clean_string).strip()
        else:
            sets = None
            reps = None
            name = clean_string

        return {
            "name": name,
            "emoji": emoji,
            "sets": sets,
            "reps": reps,
            "full_string": exercise_string
        }

    def get_workout_exercises_structured(self, workout_id: str) -> list:
        """
        Get structured exercise list for a workout.
        Returns list of exercise dicts with name, sets, reps, emoji.
        """
        from database.db_manager import get_exercises_by_workout

        exercises_data = get_exercises_by_workout(workout_id)
        structured_exercises = []

        for ex in exercises_data:
            exercise_name = ex['exercise_name']
            details = self.get_exercise_details(exercise_name)
            structured_exercises.append(details)

        return structured_exercises

