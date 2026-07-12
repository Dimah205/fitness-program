"""
Smart AI Agent Module
Analyzes user responses to detect if workouts were truly completed.
"""

import random
from database.db_manager import save_agent_prompt, update_prompt_reply, generate_short_id


class AgentAI:
    """
    Intelligent AI Agent that:
    1. Asks meaningful questions after workouts
    2. Analyzes responses to detect honesty
    3. Rejects workouts if user is lying
    """

    def __init__(self):
        self.__questions_pool = {
            "verification": [
                "What exercise did you find most challenging today?",
                "Which muscle group felt the most worked?",
                "How many reps did you manage on your last set?",
                "Did you warm up before starting?",
                "How does your body feel right now - any specific muscle soreness?",
                "Tell me exactly which exercises you did and how many sets?",
                "How long did your workout actually take in minutes?",
            ]
        }

    def monitor_user(self):
        print("👁️ AI Agent is monitoring user activity...")

    def send_random_question(self, workout_id: str, category: str = None) -> str:
        message = random.choice(self.__questions_pool["verification"])
        prompt_id = generate_short_id('A')
        save_agent_prompt(prompt_id, workout_id, message)
        print(f"\n🤖 [AI Coach] {message}")
        return prompt_id

    def receive_user_reply(self, prompt_id: str, reply: str) -> bool:
        update_prompt_reply(prompt_id, reply)
        print(f"💬 Reply saved: '{reply}'")
        return True

    def analyze_response(self, reply: str) -> dict:
        """
        Smart analysis: Returns honesty score 0-100.
        High score = honest, Low score = lying.
        """
        reply_lower = reply.lower().strip()
        words = reply_lower.split()
        word_count = len(words)

        analysis = {
            "honesty_score": 50,
            "reasons": [],
            "recommendation": "verify"
        }

        # === AUTO-REJECT: Very short answers ===
        if word_count <= 2:
            analysis["honesty_score"] = 10
            analysis["reasons"].append("Response too short - no details provided")
            analysis["recommendation"] = "reject"
            return analysis

        # === AUTO-REJECT: Generic one-word answers ===
        if reply_lower in ['yes', 'yeah', 'yep', 'done', 'ok', 'okay', 'k', 'fine', 'sure', 'no', 'nope', 'nah']:
            analysis["honesty_score"] = 15
            analysis["reasons"].append("Generic answer with no workout details")
            analysis["recommendation"] = "reject"
            return analysis

        # === Check for specific exercise names ===
        exercise_words = ['pushup', 'push up', 'squat', 'plank', 'lunge', 'burpee',
                         'jumping jack', 'mountain climber', 'high knee', 'crunch',
                         'sit up', 'pull up', 'dip', 'curl', 'press', 'row']
        mentioned_exercises = [ex for ex in exercise_words if ex in reply_lower]

        if mentioned_exercises:
            analysis["honesty_score"] += 20
            analysis["reasons"].append(f"Mentioned exercises: {', '.join(mentioned_exercises[:3])}")

        # === Check for numbers (reps/sets/time) ===
        import re
        numbers_found = re.findall(r'(\d+)\s*(sets?|reps?|minutes?|mins?|seconds?|kg|lbs?)', reply_lower)
        if numbers_found:
            analysis["honesty_score"] += 25
            analysis["reasons"].append(f"Mentioned specific numbers: {numbers_found[0][0]} {numbers_found[0][1]}")

        # === Check for effort/fatigue words ===
        effort_words = ['tired', 'exhausted', 'sore', 'aching', 'burn', 'sweat',
                       'struggled', 'hard', 'challenging', 'difficult', 'drained']
        found_effort = [w for w in effort_words if w in reply_lower]
        if found_effort:
            analysis["honesty_score"] += 20
            analysis["reasons"].append("Shows signs of physical effort")

        # === AUTO-REJECT: Claims everything was perfect/easy ===
        perfect_words = ['perfect', 'too easy', 'no problem', 'piece of cake', '100%']
        if any(p in reply_lower for p in perfect_words):
            analysis["honesty_score"] -= 30
            analysis["reasons"].append("Claims everything was perfect - suspicious")

        # === Final decision ===
        if analysis["honesty_score"] >= 60:
            analysis["recommendation"] = "accept"
        elif analysis["honesty_score"] >= 30:
            analysis["recommendation"] = "verify"
        else:
            analysis["recommendation"] = "reject"

        print(f"📊 Analysis: Score={analysis['honesty_score']}, Decision={analysis['recommendation']}")
        return analysis

    def validate_workout_completion(self, user_id: str, workout_id: str, user_reply: str) -> dict:
        analysis = self.analyze_response(user_reply)

        result = {
            "analysis": analysis,
            "workout_accepted": False,
            "message": "",
            "flagged_for_review": False
        }

        if analysis["recommendation"] == "accept":
            result["workout_accepted"] = True
            result["message"] = "✅ Workout verified! Great job!"
        elif analysis["recommendation"] == "reject":
            result["workout_accepted"] = False
            result["message"] = "❌ Could not verify this workout. Please be honest!"
            from database.db_manager import revert_workout_completion
            revert_workout_completion(workout_id)
        else:
            result["workout_accepted"] = False
            result["message"] = "🤔 Please provide more details about your workout."

        return result

    def ask_follow_up(self, workout_id: str, previous_reply: str) -> str:
        message = "Can you tell me specifically which exercises you did and how many?"
        prompt_id = generate_short_id('A')
        save_agent_prompt(prompt_id, workout_id, message)
        print(f"\n🤖 [AI Follow-up] {message}")
        return prompt_id

    def check_engagement(self, user_id: str) -> dict:
        from database.db_manager import get_user_prompt_stats
        stats = get_user_prompt_stats(user_id)
        total = stats.get('total', 0)
        replied = stats.get('replied', 0)
        reply_rate = stats.get('reply_rate', 0)

        if total == 0:
            engagement = "No data yet"
        elif reply_rate >= 80:
            engagement = "Highly Engaged 🌟"
        elif reply_rate >= 50:
            engagement = "Moderately Engaged 👍"
        else:
            engagement = "Low Engagement ⚠️"

        return {
            "total_prompts": total,
            "replied": replied,
            "reply_rate": reply_rate,
            "engagement_level": engagement
        }


# ==================== NEW WORKOUT VERIFICATION SYSTEM ====================

class WorkoutSession:
    """Manages a single workout session with questions during exercises."""

    # Multiple choice questions bank
    QUESTIONS_BANK = [
        {
            "question": "How many sets did you do in this exercise?",
            "options": ["3 sets", "4 sets", "5 sets", "6 sets"],
            "correct": "3 sets"
        },
        {
            "question": "What was the hardest part of this exercise?",
            "options": ["Lowering down", "Lifting up", "Balance", "Breathing"],
            "correct": "Lowering down"
        },
        {
            "question": "Which muscle felt the most tired?",
            "options": ["Legs", "Chest", "Back", "Abs", "Shoulders", "Arms"],
            "correct": "Legs"
        },
        {
            "question": "Did you complete all repetitions?",
            "options": ["Yes, completely", "I missed 1-2 reps", "I missed more", "I barely finished"],
            "correct": "Yes, completely"
        },
        {
            "question": "What is your fatigue level?",
            "options": ["Light", "Moderate", "Very intense", "I did not get tired"],
            "correct": "Very intense"
        },
        {
            "question": "Was your breathing correct during the exercise?",
            "options": ["Yes", "No", "Sometimes", "I didn't notice"],
            "correct": "Yes"
        },
        {
            "question": "How many seconds did you rest between sets?",
            "options": ["30 seconds", "45 seconds", "60 seconds", "90 seconds"],
            "correct": "60 seconds"
        },
        {
            "question": "Did you use the appropriate weight?",
            "options": ["Yes, appropriate", "A bit light", "Too heavy", "I don't know"],
            "correct": "Yes, appropriate"
        },
        {
            "question": "How was your body posture?",
            "options": ["Excellent", "Good", "Needs improvement", "Bad"],
            "correct": "Good"
        }
    ]

    @staticmethod
    def select_random_questions(total_exercises: int, num_questions: int = 3) -> list:
        """Randomly select which exercise indices will have questions."""
        if total_exercises <= num_questions:
            return list(range(total_exercises))

        import random
        return sorted(random.sample(range(total_exercises), num_questions))

    @staticmethod
    def get_random_question() -> dict:
        """Get a random question from the bank."""
        import random
        question_data = random.choice(WorkoutSession.QUESTIONS_BANK).copy()
        random.shuffle(question_data["options"])
        return question_data

    @staticmethod
    def check_answer(question_data: dict, selected_option: str) -> bool:
        """Check if selected answer is correct."""
        return selected_option == question_data["correct"]

    @staticmethod
    def evaluate_session(correct_answers: int, total_questions: int) -> dict:
        """Evaluate if the workout session is passed."""
        if total_questions == 0:
            return {"success": True, "message": "No questions asked"}

        success = correct_answers >= 2  # 2/3 or 3/3 = success
        return {
            "success": success,
            "correct": correct_answers,
            "total": total_questions,
            "message": "Workout completed! 🎉" if success else "Please redo this workout from the beginning. ❌"
        }