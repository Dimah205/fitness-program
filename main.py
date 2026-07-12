from models.user import User
from models.fitness_preferences import FitnessPreferences
from models.ai_engine import AIEngine
from models.health_data_fetcher import HealthDataFetcher
from models.agent_ai import AgentAI
from database.create_tables import create_database_and_tables
from database.db_manager import save_health_data, save_fitness_preferences, get_user_program
from datetime import datetime
import os


def main():
    # Create database tables if they don't exist
    create_database_and_tables()

    print("\n=== Fitness AI Application ===\n")
    print("Welcome to Your Personal AI Fitness Trainer!\n")

    choice = input("1. Register\n2. Login\nChoose: ")

    if choice == '1':
        print("\n--- User Registration ---")
        phone = input("Phone number (e.g., +905551234567): ")
        email = input("Email address: ")
        password = input("Password: ")

        # Create user object
        user = User(phone, email, password)

        # Register - sends verification email
        result = user.register()

        if result == "exists":
            print("\n⚠️ This email is already registered. Please login instead.")
            return

        if result == "verification_sent":
            print(f"\n📧 A verification code has been sent to {email}")
            print("   Please check your inbox (and spam folder).")

            # Ask for verification code
            code = input("\nEnter verification code: ")

            if user.verify_email_and_create(code):
                print("\n✅ Email verified successfully!")
                print("Now let's complete your profile...\n")

                # Continue with health data and preferences
                complete_profile(user)
            else:
                print("\n❌ Verification failed. Please try registering again.")
                return

    elif choice == '2':
        print("\n--- Login ---")
        email = input("Email: ")
        password = input("Password: ")
        user = User("", email, "")

        # Login with password only (no 2FA)
        if user.login(password):
            print("\n✅ Login successful!\n")

            user_id = user.get_user_id()

            # Check if user has an existing program in database
            ai = AIEngine()
            program = ai.load_program_from_database(user_id)

            if program:
                user.set_fitness_program(program)
                print("--- Your Current Fitness Program ---")
                program.view_plan()

                # Show workout tracking option
                workout_tracking_menu(user)

                view_history = input("\n📜 View your workout history? (y/n): ").lower()
                if view_history == 'y':
                    from database.db_manager import get_user_workout_history
                    history = get_user_workout_history(user_id)

                    if history:
                        print("\n--- Your Workout History ---")
                        for record in history:
                            print(f"✅ Day {record['day_number']} - Completed: {record['completed_date']}")
                    else:
                        print("📭 No workout history yet. Complete some workouts first!")
                # AI Agent check-in
                agent = AgentAI()
                agent.monitor_user()

                # AI Coach Menu
                print("\n--- AI Coach Menu ---")
                print("1. Answer pending questions")
                print("2. Check engagement stats")
                print("3. Skip")
                agent_choice = input("Choose: ")

                if agent_choice == '1':
                    from database.db_manager import get_unanswered_prompts
                    pending = get_unanswered_prompts(user_id)

                    if pending:
                        print(f"\n📋 You have {len(pending)} pending questions:")
                        for p in pending:
                            print(f"\n🤖 Day {p['day_number']}: {p['message']}")
                            reply = input("Your reply: ")
                            if reply:
                                agent.receive_user_reply(p['prompt_id'], reply)
                    else:
                        print("✅ No pending questions!")

                elif agent_choice == '2':
                    stats = agent.check_engagement(user_id)
                    print(f"\n📊 Engagement Stats:")
                    print(f"   Total Prompts: {stats['total_prompts']}")
                    print(f"   Replied: {stats['replied']}")
                    print(f"   Reply Rate: {stats['reply_rate']}%")
                    print(f"   Level: {stats['engagement_level']}")


                # Get first workout ID from database and send question
                program_data = get_user_program(user_id)
                if program_data:
                    from database.db_manager import get_workouts_by_program
                    workouts = get_workouts_by_program(program_data['program_id'])
                    if workouts:
                        prompt_id = agent.send_random_question(workouts[0]['workout_id'])

                        # Ask if user wants to reply now
                        reply_now = input("\n💬 Would you like to reply to the AI Coach? (y/n): ").lower()
                        if reply_now == 'y':
                            reply = input("Your reply: ")
                            if reply:
                                agent.receive_user_reply(prompt_id, reply)
                                print("✅ Thank you for your feedback!")

                                # Offer follow-up
                                follow_up = input("\n🤖 AI Coach wants to ask a follow-up. Continue? (y/n): ").lower()
                                if follow_up == 'y':
                                    agent.ask_follow_up(workouts[0]['workout_id'], reply)

                        print("\n👋 See you next time! Keep up the great work!\n")
            else:
                print("⚠️ No active program found in database.")
                print("   Would you like to create one now? (y/n): ", end="")
                create_new = input().lower()
                if create_new == 'y':
                    complete_profile(user)
        else:
            print("❌ Login failed. Please check your email and password.")


def workout_tracking_menu(user):

    user_id = user.get_user_id()
    ai = AIEngine()

    program_data = ai.get_program_with_progress(user_id)

    if not program_data:
        print("❌ No active program found.")
        return

    print("\n--- Workout Tracking ---")
    print(f"📊 Overall Progress: {program_data['progress']['percentage']}%")
    print(f"   Completed: {program_data['progress']['completed']}/{program_data['progress']['total']} days")

    # Show progress bar
    if program_data['progress']['total'] > 0:
        bar_length = 20
        filled = int(bar_length * program_data['progress']['completed'] / program_data['progress']['total'])
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"   [{bar}]")

    print("\n--- Today's Workout ---")

    if program_data['next_workout']:
        next_day = program_data['next_workout']['day']
        next_id = program_data['next_workout']['workout_id']
        print(f"⏳ Day {next_day} is waiting for you!")

        complete = input(f"\nMark Day {next_day} as completed? (y/n): ").lower()
        if complete == 'y':
            result = ai.complete_workout(user_id, next_id)
            if result['success']:
                print(f"\n✅ {result['message']}")
                print(f"📊 New Progress: {result['progress']['percentage']}%")

                # Agent asks question after workout completion
                agent = AgentAI()
                prompt_id = agent.send_random_question(next_id)

                # Ask if user wants to reply now
                reply_now = input("\n💬 Would you like to reply now? (y/n): ").lower()
                if reply_now == 'y':
                    reply = input("Your reply: ")
                    agent.receive_user_reply(prompt_id, reply)

                    # Check if follow-up needed
                    follow_up = input("\n🤖 AI Coach wants to ask a follow-up. Continue? (y/n): ").lower()
                    if follow_up == 'y':
                        agent.ask_follow_up(next_id, reply)

                if result['next_workout']:
                    print(f"\n🎯 Next workout: Day {result['next_workout']['day']}")
                else:
                    print("\n🎉 Congratulations! You've completed all workouts!")
    else:
        print("🎉 All workouts completed! Great job!")

def complete_profile(user):
    """
    Complete user profile after email verification.
    Collects health data and fitness preferences, then generates program.
    """
    user_id = user.get_user_id()

    # --- Health Data Section (e-Nabız PDF) ---
    print("\n--- Health Data (e-Nabız PDF Upload) ---")
    pdf_path = input("Enter path to your health PDF file (or press Enter to skip): ").strip()
    pdf_path = pdf_path.strip('"').strip("'")

    health_data = None

    if pdf_path:
        if os.path.exists(pdf_path):
            print(f"📄 Reading PDF: {pdf_path}")
            fetcher = HealthDataFetcher()
            health_data = fetcher.fetch_health_data_from_pdf(pdf_path)
            if health_data:
                print("✅ Health data extracted successfully!")
            else:
                print("⚠️ Could not extract data from PDF. Using default values.")
        else:
            print(f"❌ File not found: {pdf_path}")
            print("   Using default health values.")
    else:
        print("   No PDF provided. Using default health values.")

    # Use default values if no health data was extracted
    if not health_data:
        health_data = {"heart_rate": 75, "weight": 70.0, "height": 170.0}

    # Save health data to database and get sync_id
    sync_id = save_health_data(
        user_id,
        health_data.get('heart_rate'),
        health_data.get('weight'),
        health_data.get('height')
    )

    print(f"   • Heart Rate: {health_data.get('heart_rate', 'N/A')} bpm")
    print(f"   • Weight: {health_data.get('weight', 'N/A')} kg")
    print(f"   • Height: {health_data.get('height', 'N/A')} cm")
    print(f"✅ Health data saved. sync_id = {sync_id}")

    # --- Fitness Preferences Section ---
    print("\n--- Fitness Preferences ---")
    print("Examples: Weight Loss, Muscle Gain, General Fitness")
    goal = input("Your fitness goal: ")

    days = int(input("Workout days per week (1-7): "))
    while days < 1 or days > 7:
        days = int(input("Please enter a number between 1 and 7: "))

    # Save preferences to database and get pref_id
    pref_id = save_fitness_preferences(user_id, goal, days)
    print(f"✅ Preferences saved. pref_id = {pref_id}")

    # --- Generate and Save Program ---
    print("\n--- Generating Your Personalized Program ---")

    preferences = FitnessPreferences(goal, days)
    ai = AIEngine()

    # Pass pref_id and sync_id to save program correctly
    program = ai.generate_and_save_program(
        user_id,
        preferences,
        health_data,
        pref_id,
        sync_id
    )
    user.set_fitness_program(program)

    print("\n" + "=" * 50)
    program.view_plan()
    print("=" * 50)

    # --- AI Coach Introduction ---
    print("\n--- Meet Your AI Coach ---")
    agent = AgentAI()
    agent.monitor_user()

    print("\n📱 Your AI coach will check in with you after each workout.")
    print("   Example question:")
    print("\n📱 Your AI coach will check in with you after you complete your first workout!")
    print("\n✅ Profile complete! Your fitness journey begins now.\n")

    print("\n--- Workout Tracking ---")
    print("You can now track your progress!")
    print("Run the program again and login to mark workouts as completed.\n")


if __name__ == "__main__":
    main()