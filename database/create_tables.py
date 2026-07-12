import mysql.connector
from mysql.connector import errorcode
from database.db_config import config


def create_database_and_tables():
    temp_config = config.copy()
    db_name = temp_config.pop('database')

    try:
        conn = mysql.connector.connect(**temp_config)
        cursor = conn.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")
        print(f"Database '{db_name}' is ready.")

        conn.database = db_name

        # -------------------------
        # Users Table
        # -------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id VARCHAR(5) PRIMARY KEY,
                phone_number VARCHAR(20) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                age INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'Users' created or already exists.")

        # -------------------------
        # FitnessPreferences Table
        # -------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FitnessPreferences (
                pref_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(5) NOT NULL UNIQUE,
                fitness_goal VARCHAR(50) NOT NULL,
                workout_days INT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )
        """)
        print("Table 'FitnessPreferences' created or already exists.")

        # -------------------------
        # ENabizSync Table
        # -------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ENabizSync (
                sync_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(5) NOT NULL UNIQUE,
                heart_rate INT,
                weight DECIMAL(5,2),
                height DECIMAL(5,2),
                sync_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )
        """)
        print("Table 'ENabizSync' created or already exists.")

        # -------------------------
        # FitnessPrograms Table
        # -------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FitnessPrograms (
                program_id VARCHAR(5) PRIMARY KEY,
                user_id VARCHAR(5) NOT NULL UNIQUE,
                pref_id INT,
                sync_id INT,
                start_date DATE NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (pref_id) REFERENCES FitnessPreferences(pref_id) ON DELETE SET NULL,
                FOREIGN KEY (sync_id) REFERENCES ENabizSync(sync_id) ON DELETE SET NULL
            )
        """)
        print("Table 'FitnessPrograms' created or already exists.")

        # -------------------------
        # Workouts Table
        # -------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Workouts (
                workout_id VARCHAR(5) PRIMARY KEY,
                program_id VARCHAR(5) NOT NULL,
                day_number INT NOT NULL,
                video_url VARCHAR(255),
                completed BOOLEAN DEFAULT FALSE,
                completed_date DATETIME,
                FOREIGN KEY (program_id) REFERENCES FitnessPrograms(program_id) ON DELETE CASCADE,
                UNIQUE KEY unique_program_day (program_id, day_number)
            )
        """)
        print("Table 'Workouts' created or already exists.")

        # -------------------------
        # WorkoutExercises Table
        # -------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS WorkoutExercises (
                exercise_id INT AUTO_INCREMENT PRIMARY KEY,
                workout_id VARCHAR(5) NOT NULL,
                exercise_name VARCHAR(100) NOT NULL,
                sets_reps VARCHAR(100),
                order_index INT NOT NULL,
                FOREIGN KEY (workout_id) REFERENCES Workouts(workout_id) ON DELETE CASCADE
            )
        """)
        print("Table 'WorkoutExercises' created or already exists.")

        # -------------------------
        # AgentPrompts Table
        # -------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AgentPrompts (
                prompt_id VARCHAR(5) PRIMARY KEY,
                workout_id VARCHAR(10) NOT NULL,
                message TEXT NOT NULL,
                user_reply TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workout_id) REFERENCES Workouts(workout_id) ON DELETE CASCADE
            )
        """)
        print("Table 'AgentPrompts' created or already exists.")

        # -------------------------
        # BodyMeasurements Table
        # -------------------------
        cursor.execute("""
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
        """)
        print("Table 'BodyMeasurements' created or already exists.")
        from database.db_manager import create_body_measurements_table
        conn.commit()
        cursor.close()
        conn.close()

        print("\n✅ All tables created successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if conn:
            conn.close()


if __name__ == "__main__":
    create_database_and_tables()