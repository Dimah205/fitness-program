import mysql.connector
from database.db_config import config
import random
import string


class DBManager:
    """Database manager class for executing queries."""

    def __init__(self):
        self.conn = mysql.connector.connect(**config)
        self.cursor = self.conn.cursor(dictionary=True)

    def execute(self, query, params=None):
        """Execute a query and commit changes."""
        self.cursor.execute(query, params or ())
        self.conn.commit()
        return self.cursor.lastrowid

    def fetch_one(self, query, params=None):
        """Fetch a single row from the database."""
        self.cursor.execute(query, params or ())
        return self.cursor.fetchone()

    def fetch_all(self, query, params=None):
        """Fetch all rows from the database."""
        self.cursor.execute(query, params or ())
        return self.cursor.fetchall()

    def close(self):
        """Close the database connection."""
        self.cursor.close()
        self.conn.close()


# ==================== Helper Functions ====================

def generate_short_id(prefix=''):
    """Generate a 5-character ID with optional prefix."""
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=3))
    return f"{prefix}{random_part}"[:5]


# ==================== User Functions ====================

def create_user(user_id, phone, email, password_hash):
    """Create a new user in the database."""
    db = DBManager()
    query = """
        INSERT INTO Users (user_id, phone_number, email, password_hash) 
        VALUES (%s, %s, %s, %s)
    """
    db.execute(query, (user_id, phone, email, password_hash))
    db.close()


def get_user_by_email(email):
    """Retrieve a user by their email address."""
    db = DBManager()
    query = "SELECT * FROM Users WHERE email = %s"
    user = db.fetch_one(query, (email,))
    db.close()
    return user


def get_user_by_id(user_id):
    """Retrieve a user by their ID."""
    db = DBManager()
    query = "SELECT * FROM Users WHERE user_id = %s"
    user = db.fetch_one(query, (user_id,))
    db.close()
    return user


def get_user_by_phone(phone_number):
    """Retrieve a user by their phone number."""
    db = DBManager()
    query = "SELECT * FROM Users WHERE phone_number = %s"
    user = db.fetch_one(query, (phone_number,))
    db.close()
    return user


# ==================== Health Data Functions ====================

def save_health_data(user_id, heart_rate, weight, height):
    """
    Save or update health data for a user.
    Returns the sync_id of the saved record.
    """
    db = DBManager()
    query = """
        INSERT INTO ENabizSync (user_id, heart_rate, weight, height)
        VALUES (%s, %s, %s, %s) AS new_data
        ON DUPLICATE KEY UPDATE
        heart_rate = new_data.heart_rate,
        weight = new_data.weight,
        height = new_data.height,
        sync_date = CURRENT_TIMESTAMP
    """
    db.execute(query, (user_id, heart_rate, weight, height))

    query = "SELECT sync_id FROM ENabizSync WHERE user_id = %s"
    result = db.fetch_one(query, (user_id,))
    sync_id = result['sync_id'] if result else None
    db.close()
    return sync_id


def get_health_data_by_user(user_id):
    """Retrieve the latest health data for a user."""
    db = DBManager()
    query = """
        SELECT heart_rate, weight, height, sync_date 
        FROM ENabizSync 
        WHERE user_id = %s
    """
    result = db.fetch_one(query, (user_id,))
    db.close()
    return result

def get_latest_health_data(user_id):
    """Get the latest health data for a user with sync_id."""
    db = DBManager()
    query = """
        SELECT heart_rate, weight, height, sync_id, sync_date 
        FROM ENabizSync 
        WHERE user_id = %s
    """
    result = db.fetch_one(query, (user_id,))
    db.close()
    return result


# ==================== Fitness Preferences Functions ====================

def save_fitness_preferences(user_id, goal, days):
    """
    Save or update fitness preferences for a user.
    Returns the pref_id of the saved record.
    """
    db = DBManager()
    query = """
        INSERT INTO FitnessPreferences (user_id, fitness_goal, workout_days)
        VALUES (%s, %s, %s) AS new_prefs
        ON DUPLICATE KEY UPDATE
        fitness_goal = new_prefs.fitness_goal,
        workout_days = new_prefs.workout_days
    """
    db.execute(query, (user_id, goal, days))

    query = "SELECT pref_id FROM FitnessPreferences WHERE user_id = %s"
    result = db.fetch_one(query, (user_id,))
    pref_id = result['pref_id'] if result else None
    db.close()
    return pref_id


def get_preferences_by_user(user_id):
    """Retrieve fitness preferences for a user."""
    db = DBManager()
    query = """
        SELECT fitness_goal, workout_days 
        FROM FitnessPreferences 
        WHERE user_id = %s
    """
    result = db.fetch_one(query, (user_id,))
    db.close()
    return result


# ==================== Fitness Program Functions ====================

def save_fitness_program(program_id, user_id, start_date, pref_id=None, sync_id=None):
    """
    Save or update a fitness program.
    """
    db = DBManager()
    query = """
        INSERT INTO FitnessPrograms (program_id, user_id, start_date, pref_id, sync_id)
        VALUES (%s, %s, %s, %s, %s) AS new_program
        ON DUPLICATE KEY UPDATE
        program_id = new_program.program_id,
        start_date = new_program.start_date,
        pref_id = new_program.pref_id,
        sync_id = new_program.sync_id,
        generated_at = CURRENT_TIMESTAMP
    """
    db.execute(query, (program_id, user_id, start_date, pref_id, sync_id))
    db.close()
    print(f"✅ Program saved with pref_id={pref_id}, sync_id={sync_id}")


def get_user_program(user_id):
    """Retrieve the fitness program for a user."""
    db = DBManager()
    query = "SELECT * FROM FitnessPrograms WHERE user_id = %s"
    program = db.fetch_one(query, (user_id,))
    db.close()
    return program


def delete_user_program(user_id):
    """Delete a user's fitness program but KEEP workout history."""
    db = DBManager()

    # Get program_id first
    query = "SELECT program_id FROM FitnessPrograms WHERE user_id = %s"
    program = db.fetch_one(query, (user_id,))

    if program:
        program_id = program['program_id']

        # Delete exercises first
        query = """
            DELETE we FROM WorkoutExercises we
            JOIN Workouts w ON we.workout_id = w.workout_id
            WHERE w.program_id = %s
        """
        db.execute(query, (program_id,))

        # Delete agent prompts
        query = """
            DELETE ap FROM AgentPrompts ap
            JOIN Workouts w ON ap.workout_id = w.workout_id
            WHERE w.program_id = %s
        """
        db.execute(query, (program_id,))

        # ✅ KEEP WorkoutHistory - DO NOT DELETE
        # The history stays even after program is deleted

        # Delete workouts (history will have orphaned workout_ids but that's ok)
        query = "DELETE FROM Workouts WHERE program_id = %s"
        db.execute(query, (program_id,))

    # Finally delete the program
    query = "DELETE FROM FitnessPrograms WHERE user_id = %s"
    db.execute(query, (user_id,))
    db.close()
    print(f"🗑️ Old program deleted but workout history kept for user {user_id}")


# ==================== Workout Functions ====================

def save_workout(workout_id, program_id, day_number, video_url):
    """Save or update a workout."""
    db = DBManager()
    # Check if this workout_id already exists
    existing = db.fetch_one("SELECT workout_id FROM Workouts WHERE workout_id = %s", (workout_id,))

    if existing:
        # Generate new unique ID
        workout_id = generate_short_id('W')

    query = """
        INSERT INTO Workouts (workout_id, program_id, day_number, video_url)
        VALUES (%s, %s, %s, %s) AS new_workout
        ON DUPLICATE KEY UPDATE
        video_url = new_workout.video_url
    """
    db.execute(query, (workout_id, program_id, day_number, video_url))
    db.close()


def save_exercise(workout_id, exercise_name, sets_reps, order_index):
    """Save an exercise for a workout."""
    db = DBManager()
    query = """
        INSERT INTO WorkoutExercises (workout_id, exercise_name, sets_reps, order_index)
        VALUES (%s, %s, %s, %s)
    """
    db.execute(query, (workout_id, exercise_name, sets_reps, order_index))
    db.close()


def get_workouts_by_program(program_id):
    """Retrieve all workouts for a program."""
    db = DBManager()
    query = "SELECT * FROM Workouts WHERE program_id = %s ORDER BY day_number"
    workouts = db.fetch_all(query, (program_id,))
    db.close()
    return workouts


def get_exercises_by_workout(workout_id):
    """Retrieve all exercises for a workout."""
    db = DBManager()
    query = "SELECT * FROM WorkoutExercises WHERE workout_id = %s ORDER BY order_index"
    exercises = db.fetch_all(query, (workout_id,))
    db.close()
    return exercises


# ==================== Workout Progress & Tracking Functions ====================

def mark_workout_completed(workout_id, completed_date):
    """Mark a workout as completed in the database."""
    db = DBManager()
    query = """
        UPDATE Workouts 
        SET completed = TRUE, completed_date = %s 
        WHERE workout_id = %s
    """
    db.execute(query, (completed_date, workout_id))
    db.close()
    return True


def save_workout_history(user_id, workout_id, completed_date):
    """Save completed workout to history table."""
    db = DBManager()
    query = """
        INSERT INTO WorkoutHistory (user_id, workout_id, completed_date)
        VALUES (%s, %s, %s)
    """
    db.execute(query, (user_id, workout_id, completed_date))
    db.close()


def get_workout_completion_status(workout_id):
    """Check if a workout is completed."""
    db = DBManager()
    query = "SELECT completed, completed_date FROM Workouts WHERE workout_id = %s"
    result = db.fetch_one(query, (workout_id,))
    db.close()
    if result:
        return {
            "completed": result['completed'],
            "completed_date": result['completed_date']
        }
    return {"completed": False, "completed_date": None}


def get_program_progress(program_id):
    """Get progress statistics for a program."""
    db = DBManager()
    query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END) as completed
        FROM Workouts 
        WHERE program_id = %s
    """
    result = db.fetch_one(query, (program_id,))
    db.close()

    if result:
        total = result['total']
        completed = result['completed'] or 0
        percentage = (completed / total * 100) if total > 0 else 0
        return {
            "total": total,
            "completed": completed,
            "percentage": round(percentage, 1)
        }
    return {"total": 0, "completed": 0, "percentage": 0}


def get_user_workout_history(user_id):
    """Get user's workout completion history."""
    db = DBManager()
    query = """
        SELECT wh.*, w.day_number, w.program_id
        FROM WorkoutHistory wh
        JOIN Workouts w ON wh.workout_id = w.workout_id
        WHERE wh.user_id = %s
        ORDER BY wh.completed_date DESC
    """
    history = db.fetch_all(query, (user_id,))
    db.close()
    return history


def get_workout_by_id(workout_id):
    """Get workout details by ID."""
    db = DBManager()
    query = "SELECT * FROM Workouts WHERE workout_id = %s"
    workout = db.fetch_one(query, (workout_id,))
    db.close()
    return workout


def get_program_by_workout(workout_id):
    """Get program ID from workout ID."""
    db = DBManager()
    query = """
        SELECT p.* 
        FROM FitnessPrograms p
        JOIN Workouts w ON p.program_id = w.program_id
        WHERE w.workout_id = %s
    """
    program = db.fetch_one(query, (workout_id,))
    db.close()
    return program


# ==================== Agent Prompts Functions ====================

def save_agent_prompt(prompt_id, workout_id, message):
    """Save an AI agent prompt to database."""
    db = DBManager()
    query = """
        INSERT INTO AgentPrompts (prompt_id, workout_id, message)
        VALUES (%s, %s, %s)
    """
    db.execute(query, (prompt_id, workout_id, message))
    db.close()


def update_prompt_reply(prompt_id, user_reply):
    """Update user's reply to a prompt."""
    db = DBManager()
    query = """
        UPDATE AgentPrompts 
        SET user_reply = %s 
        WHERE prompt_id = %s
    """
    db.execute(query, (user_reply, prompt_id))
    db.close()


def get_prompts_by_workout(workout_id):
    """Get all prompts for a specific workout."""
    db = DBManager()
    query = """
        SELECT * FROM AgentPrompts 
        WHERE workout_id = %s 
        ORDER BY sent_at DESC
    """
    prompts = db.fetch_all(query, (workout_id,))
    db.close()
    return prompts


def get_user_prompt_stats(user_id):
    """Get prompt statistics for a user."""
    db = DBManager()
    query = """
        SELECT 
            COUNT(ap.prompt_id) as total_prompts,
            SUM(CASE WHEN ap.user_reply IS NOT NULL THEN 1 ELSE 0 END) as replied_prompts
        FROM AgentPrompts ap
        JOIN Workouts w ON ap.workout_id = w.workout_id
        JOIN FitnessPrograms fp ON w.program_id = fp.program_id
        WHERE fp.user_id = %s
    """
    result = db.fetch_one(query, (user_id,))
    db.close()

    total = result['total_prompts'] if result else 0
    replied = result['replied_prompts'] if result else 0
    reply_rate = (replied / total * 100) if total > 0 else 0

    return {
        "total": total,  # ✅ تغيير المفتاح هنا
        "replied": replied,
        "reply_rate": round(reply_rate, 1)
    }


def get_unanswered_prompts(user_id):
    """Get all unanswered prompts for a user."""
    db = DBManager()
    query = """
        SELECT ap.*, w.day_number
        FROM AgentPrompts ap
        JOIN Workouts w ON ap.workout_id = w.workout_id
        JOIN FitnessPrograms fp ON w.program_id = fp.program_id
        WHERE fp.user_id = %s AND ap.user_reply IS NULL
        ORDER BY ap.sent_at DESC
    """
    prompts = db.fetch_all(query, (user_id,))
    db.close()
    return prompts


# ==================== Body Measurements Functions ====================

def create_body_measurements_table():
    """Create body measurements table if not exists."""
    db = DBManager()
    query = """
        CREATE TABLE IF NOT EXISTS BodyMeasurements (
            measurement_id VARCHAR(5) PRIMARY KEY,
            user_id VARCHAR(5) NOT NULL,
            weight DECIMAL(5,2) NOT NULL,
            chest DECIMAL(5,2),
            waist DECIMAL(5,2),
            hips DECIMAL(5,2),
            arms DECIMAL(5,2),
            thighs DECIMAL(5,2),
            notes TEXT,
            recorded_date DATE NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        )
    """
    db.execute(query)
    db.close()
    print("Table 'BodyMeasurements' created or already exists.")


def save_body_measurement(user_id, weight, chest=None, waist=None,
                          hips=None, arms=None, thighs=None, notes=None):
    """Save a body measurement record."""
    db = DBManager()
    from datetime import datetime

    measurement_id = generate_short_id('M')
    recorded_date = datetime.now().strftime("%Y-%m-%d")

    query = """
        INSERT INTO BodyMeasurements 
        (measurement_id, user_id, weight, chest, waist, hips, arms, thighs, notes, recorded_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    db.execute(query, (measurement_id, user_id, weight, chest, waist,
                       hips, arms, thighs, notes, recorded_date))
    db.close()
    return measurement_id


def get_user_measurements(user_id, limit=30):
    """Get user's measurement history."""
    db = DBManager()
    query = """
        SELECT * FROM BodyMeasurements 
        WHERE user_id = %s 
        ORDER BY recorded_date DESC 
        LIMIT %s
    """
    measurements = db.fetch_all(query, (user_id, limit))
    db.close()
    return measurements


def get_latest_measurement(user_id):
    """Get user's most recent measurement."""
    db = DBManager()
    query = """
        SELECT * FROM BodyMeasurements 
        WHERE user_id = %s 
        ORDER BY recorded_date DESC 
        LIMIT 1
    """
    result = db.fetch_one(query, (user_id,))
    db.close()
    return result


def get_weight_progress(user_id):
    """Get weight history for chart."""
    db = DBManager()
    query = """
        SELECT weight, recorded_date 
        FROM BodyMeasurements 
        WHERE user_id = %s 
        ORDER BY recorded_date ASC
    """
    data = db.fetch_all(query, (user_id,))
    db.close()
    return data


def revert_workout_completion(workout_id):
    """
    Mark a workout as NOT completed (if lying detected).
    Also remove from history.
    """
    db = DBManager()
    query = """
        UPDATE Workouts 
        SET completed = FALSE, completed_date = NULL 
        WHERE workout_id = %s
    """
    db.execute(query, (workout_id,))

    # Remove from history
    query = "DELETE FROM WorkoutHistory WHERE workout_id = %s"
    db.execute(query, (workout_id,))
    db.close()
    print(f"⚠️ Workout {workout_id} reverted to incomplete (suspicious activity)")
    return True


# أضف هذه الدوال في database/db_manager.py

def get_workout_with_exercises(workout_id: str, get_db_connection=None) -> dict:
    """Get workout with all its exercises."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get workout
    cursor.execute("SELECT * FROM workouts WHERE workout_id = ?", (workout_id,))
    workout = cursor.fetchone()

    if not workout:
        conn.close()
        return None

    # Get exercises
    cursor.execute("SELECT * FROM exercises WHERE workout_id = ? ORDER BY exercise_order", (workout_id,))
    exercises = cursor.fetchall()

    conn.close()

    return {
        "workout_id": workout["workout_id"],
        "day_number": workout["day_number"],
        "program_id": workout["program_id"],
        "completed": workout["completed"],
        "completed_date": workout["completed_date"],
        "video_url": workout["video_url"],
        "exercises": [dict(ex) for ex in exercises]
    }


def get_all_workouts_by_week(user_id: str, get_db_connection=None) -> dict:
    """Get all workouts organized by week."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get user's program
    cursor.execute("""
        SELECT p.*, fp.goal, fp.days_per_week 
        FROM programs p
        JOIN fitness_preferences fp ON p.pref_id = fp.pref_id
        WHERE p.user_id = ? AND p.is_active = 1
        ORDER BY p.start_date DESC LIMIT 1
    """, (user_id,))

    program = cursor.fetchone()
    if not program:
        conn.close()
        return None

    # Get all workouts for this program
    cursor.execute("""
        SELECT w.*, 
               GROUP_CONCAT(e.exercise_name, '|||') as exercises_list
        FROM workouts w
        LEFT JOIN exercises e ON w.workout_id = e.workout_id
        WHERE w.program_id = ?
        GROUP BY w.workout_id
        ORDER BY w.day_number
    """, (program["program_id"],))

    workouts = cursor.fetchall()
    conn.close()

    # Group by week
    days_per_week = program["days_per_week"]
    weeks = []

    for i in range(0, len(workouts), days_per_week):
        week_workouts = workouts[i:i + days_per_week]
        week_number = i // days_per_week + 1

        week_data = {
            "week_number": week_number,
            "workouts": [],
            "completed": sum(1 for w in week_workouts if w["completed"]),
            "total": len(week_workouts)
        }

        for w in week_workouts:
            exercises = w["exercises_list"].split("|||") if w["exercises_list"] else []
            week_data["workouts"].append({
                "workout_id": w["workout_id"],
                "day_number": w["day_number"],
                "completed": bool(w["completed"]),
                "completed_date": w["completed_date"],
                "video_url": w["video_url"],
                "exercises": exercises
            })

        week_data["progress"] = round((week_data["completed"] / week_data["total"]) * 100, 1) if week_data[
                                                                                                     "total"] > 0 else 0
        weeks.append(week_data)

    return {
        "program_id": program["program_id"],
        "start_date": program["start_date"],
        "goal": program["goal"],
        "days_per_week": days_per_week,
        "weeks": weeks,
        "total_workouts": len(workouts),
        "completed_workouts": sum(1 for w in workouts if w["completed"]),
        "progress_percentage": round((sum(1 for w in workouts if w["completed"]) / len(workouts)) * 100,
                                     1) if workouts else 0
    }


# أضف هذه الدوال في نهاية ملف database/db_manager.py

def get_workout_with_exercises(workout_id: str) -> dict:
    """Get workout with all its exercises."""
    db = DBManager()

    # Get workout
    workout = db.fetch_one("SELECT * FROM workouts WHERE workout_id = %s", (workout_id,))

    if not workout:
        db.close()
        return None

    # Get exercises
    exercises = db.fetch_all(
        "SELECT * FROM exercises WHERE workout_id = %s ORDER BY exercise_order",
        (workout_id,)
    )

    db.close()

    return {
        "workout_id": workout["workout_id"],
        "day_number": workout["day_number"],
        "program_id": workout["program_id"],
        "completed": workout["completed"],
        "completed_date": workout["completed_date"],
        "video_url": workout["video_url"],
        "exercises": exercises
    }


def get_all_workouts_by_week(user_id: str) -> dict:
    """Get all workouts organized by week."""
    db = DBManager()

    # Get user's program
    query = """
        SELECT p.*, fp.fitness_goal as goal, fp.workout_days as days_per_week 
        FROM fitnessprograms p
        JOIN fitnesspreferences fp ON p.pref_id = fp.pref_id
        WHERE p.user_id = %s
        ORDER BY p.start_date DESC LIMIT 1
    """
    program = db.fetch_one(query, (user_id,))

    if not program:
        db.close()
        return None

    # Get all workouts for this program
    query = """
        SELECT w.*, 
               GROUP_CONCAT(e.exercise_name SEPARATOR '|||') as exercises_list
        FROM workouts w
        LEFT JOIN exercises e ON w.workout_id = e.workout_id
        WHERE w.program_id = %s
        GROUP BY w.workout_id
        ORDER BY w.day_number
    """
    workouts = db.fetch_all(query, (program["program_id"],))
    db.close()

    # Group by week
    days_per_week = program["days_per_week"]
    weeks = []

    for i in range(0, len(workouts), days_per_week):
        week_workouts = workouts[i:i + days_per_week]
        week_number = i // days_per_week + 1

        week_data = {
            "week_number": week_number,
            "workouts": [],
            "completed": sum(1 for w in week_workouts if w["completed"]),
            "total": len(week_workouts)
        }

        for w in week_workouts:
            exercises = w["exercises_list"].split("|||") if w["exercises_list"] else []
            week_data["workouts"].append({
                "workout_id": w["workout_id"],
                "day_number": w["day_number"],
                "completed": bool(w["completed"]),
                "completed_date": w["completed_date"],
                "video_url": w["video_url"],
                "exercises": exercises
            })

        week_data["progress"] = round((week_data["completed"] / week_data["total"]) * 100, 1) if week_data[
                                                                                                     "total"] > 0 else 0
        weeks.append(week_data)

    total_workouts = len(workouts)
    completed_workouts = sum(1 for w in workouts if w["completed"])

    return {
        "program_id": program["program_id"],
        "start_date": program["start_date"],
        "goal": program["goal"],
        "days_per_week": days_per_week,
        "weeks": weeks,
        "total_workouts": total_workouts,
        "completed_workouts": completed_workouts,
        "progress_percentage": round((completed_workouts / total_workouts) * 100, 1) if total_workouts > 0 else 0
    }
def get_preferences_by_user(user_id: str) -> dict:
    """Retrieve fitness preferences for a user."""
    db = DBManager()
    query = """
        SELECT fitness_goal, workout_days 
        FROM FitnessPreferences 
        WHERE user_id = %s
    """
    result = db.fetch_one(query, (user_id,))
    db.close()
    return result

def update_user_age(user_id: str, age: int):
    """Update user's age in Users table."""
    db = DBManager()
    query = """
        UPDATE Users 
        SET age = %s 
        WHERE user_id = %s
    """
    db.execute(query, (age, user_id))
    db.close()
    print(f"✅ Age updated for user {user_id}: {age}")

def get_user_age(user_id: str) -> int:
    """Get user's age from Users table."""
    db = DBManager()
    query = "SELECT age FROM Users WHERE user_id = %s"
    result = db.fetch_one(query, (user_id,))
    db.close()
    return result['age'] if result else None

def update_user_password(user_id: str, new_password: str):
    """Update user's password."""
    from utils.password_utils import hash_password
    db = DBManager()
    password_hash = hash_password(new_password)
    query = "UPDATE Users SET password_hash = %s WHERE user_id = %s"
    db.execute(query, (password_hash, user_id))
    db.close()