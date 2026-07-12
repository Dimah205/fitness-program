from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_cors import CORS
import os
import tempfile
import random
from datetime import datetime
from dotenv import load_dotenv
from models.body_measurements import BodyTracker
from models.report_generator import ReportGenerator
from database.db_manager import (
    save_health_data, save_fitness_preferences,
    get_user_workout_history, get_user_by_id,
    get_user_program, delete_user_program, get_latest_health_data,
    get_latest_measurement, get_user_measurements, get_weight_progress,
    save_body_measurement
)
load_dotenv()

# ── Import your existing backend models ──
from models.user import User
from models.two_factor_auth import TwoFactorAuth
from models.ai_engine import AIEngine
from models.fitness_preferences import FitnessPreferences
from models.health_data_fetcher import HealthDataFetcher
from models.agent_ai import AgentAI, WorkoutSession
from database.db_manager import (
    save_health_data, save_fitness_preferences,
    get_user_workout_history, get_user_by_id
)
from database.create_tables import create_database_and_tables

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-in-production')
CORS(app, supports_credentials=True)

# Create DB tables on startup
create_database_and_tables()

# ─────────────────────────────────────────
#  In-memory store for pending 2FA codes
#  (keyed by email → TwoFactorAuth instance)
#  In production, use Redis or DB instead
# ─────────────────────────────────────────
pending_2fa = {}


# ════════════════════════════════════════
#  PAGE ROUTES
# ════════════════════════════════════════

@app.route('/')
def index():
    """Landing page — login/register."""
    if session.get('authenticated'):
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """Main dashboard — requires login."""
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('dashboard.html')


@app.route('/program')
def program():
    """Program view page."""
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('program.html')


@app.route('/history')
def history():
    """Workout history page."""
    if not session.get('authenticated'):
        return redirect(url_for('index'))



@app.route('/profile')
def profile():
    """Profile/settings page."""
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('profile.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """
    Step 1 of registration.
    """
    data = request.get_json()
    email    = data.get('email', '').strip()
    phone    = data.get('phone_number', '').strip()
    password = data.get('password', '')

    if not all([email, phone, password]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    user   = User(phone, email, password)
    result = user.register()

    if result == 'exists':
        return jsonify({'success': False, 'message': 'This email is already registered.'}), 400

    if result == 'verification_sent':
        # Store temp user data AND verification code/expiry
        session['temp_user'] = {'phone': phone, 'email': email, 'password': password}
        session['verification_data'] = {
            'code': user._User__verification_code,
            'expiry': user._User__code_expiry.isoformat() if user._User__code_expiry else None
        }
        return jsonify({'success': True, 'message': 'Verification code sent.'}), 200

    return jsonify({'success': False, 'message': 'Registration failed.'}), 500

@app.route('/api/auth/verify-email', methods=['POST'])
def api_verify_email():
    """
    Step 2 of registration — verify email code.
    """
    data = request.get_json()
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()

    temp = session.get('temp_user')
    if not temp or temp.get('email') != email:
        return jsonify({'success': False, 'message': 'No pending registration for this email.'}), 400

    # Create user with stored data
    user = User(temp['phone'], temp['email'], temp['password'])

    # Manually set verification code and expiry from session
    # (because register() was called in api_register, not here)
    verification_data = session.get('verification_data')
    if verification_data:
        user._User__verification_code = verification_data.get('code')
        from datetime import datetime
        expiry_str = verification_data.get('expiry')
        if expiry_str:
            user._User__code_expiry = datetime.fromisoformat(expiry_str)
        else:
            user._User__code_expiry = datetime.now()
    else:
        return jsonify({'success': False, 'message': 'Verification expired. Please register again.'}), 400

    if user.verify_email_and_create(code):
        session.pop('temp_user', None)
        session.pop('verification_data', None)
        session['pending_user_id'] = user.get_user_id()
        return jsonify({
            'success': True,
            'reg_token': user.get_user_id()
        }), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid or expired code.'}), 400


@app.route('/api/user/profile', methods=['POST'])
def api_save_profile():
    """
    Step 3 of registration - save health data + preferences, generate program.
    Also saves initial body measurements from PDF.
    """
    auth_header = request.headers.get('Authorization', '')
    user_id = auth_header.replace('Bearer ', '').strip()

    if not user_id:
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    goal = request.form.get('goal', '').strip()
    days = request.form.get('days', '0').strip()

    if not goal or not days.isdigit() or not (1 <= int(days) <= 7):
        return jsonify({'success': False, 'message': 'Invalid goal or days.'}), 400

    days = int(days)
    health_data = {'heart_rate': 75, 'weight': 70.0, 'height': 170.0}

    # Extract health data from uploaded PDF if provided
    pdf_file = request.files.get('pdf_file')
    if pdf_file and pdf_file.filename.endswith('.pdf'):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            pdf_file.save(tmp.name)
            tmp_path = tmp.name

        fetcher = HealthDataFetcher()
        extracted = fetcher.fetch_health_data_from_pdf(tmp_path)
        if extracted:
            health_data = extracted

            # ✅ NEW: Save initial body measurement from PDF data
            from database.db_manager import save_body_measurement
            save_body_measurement(
                user_id=user_id,
                weight=extracted.get('weight', 70.0),
                chest=None,  # PDF usually doesn't have these
                waist=None,
                hips=None,
                notes="Initial measurement from e-Nabız PDF"
            )
            print(f"✅ Initial body measurement saved from PDF for user {user_id}")

        try:
            os.unlink(tmp_path)
        except:
            pass

    # Save to DB
    sync_id = save_health_data(
        user_id,
        health_data.get('heart_rate'),
        health_data.get('weight'),
        health_data.get('height')
    )

    pref_id = save_fitness_preferences(user_id, goal, days)

    # Generate program
    prefs = FitnessPreferences(goal, days)
    ai = AIEngine()
    ai.generate_and_save_program(user_id, prefs, health_data, pref_id, sync_id)

    return jsonify({
        'success': True,
        'message': 'Profile saved, measurements recorded, and program generated.'
    }), 200


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """
    Login with email and password only (no 2FA required).
    """
    data     = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

    user = User('', email, '')
    if not user.login(password):
        return jsonify({'success': False, 'message': 'Incorrect email or password.'}), 401

    # Login successful - set session directly (no 2FA)
    from database.db_manager import get_user_by_email
    user_data = get_user_by_email(email)
    user_id   = user_data['user_id']

    session['user_id']       = user_id
    session['authenticated'] = True
    session['user_email']    = email

    return jsonify({'success': True, 'user_id': user_id, 'message': 'Login successful!'}), 200

@app.route('/api/auth/verify-2fa', methods=['POST'])
def api_verify_2fa():
    """
    Login step 2 — verify 2FA code.
    Body: { email, code }
    Calls: TwoFactorAuth.verify_code(code)
    Returns: { success: true, user_id } and sets session
    """
    data  = request.get_json()
    email = data.get('email', '').strip()
    code  = data.get('code', '').strip()

    tfa = pending_2fa.get(email)
    if not tfa:
        return jsonify({'success': False, 'message': 'No pending 2FA for this email.'}), 400

    if not tfa.verify_code(code):
        return jsonify({'success': False, 'message': 'Invalid or expired code.'}), 401

    # Clean up and create session
    pending_2fa.pop(email, None)

    from database.db_manager import get_user_by_email
    user_data = get_user_by_email(email)
    user_id   = user_data['user_id']

    session['user_id']       = user_id
    session['authenticated'] = True
    session['user_email']    = email

    return jsonify({'success': True, 'user_id': user_id}), 200


# ════════════════════════════════════════
#  PROGRAM ROUTES
# ════════════════════════════════════════

@app.route('/api/program', methods=['GET'])
def api_get_program():
    """Get user's active program with progress."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    ai           = AIEngine()
    program_data = ai.get_program_with_progress(session['user_id'])

    if not program_data:
        return jsonify({'success': False, 'message': 'No active program found.'}), 404

    return jsonify({'success': True, 'data': program_data}), 200


@app.route('/api/program/generate', methods=['POST'])
def api_generate_program():
    """
    Generate a new program (replaces existing one).
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    data = request.get_json()
    goal = data.get('goal', '').strip()
    days = data.get('days', 0)
    user_id = session['user_id']

    if not goal or not (1 <= int(days) <= 7):
        return jsonify({'success': False, 'message': 'Invalid goal or days.'}), 400

    days = int(days)

    # Get latest health data
    health_data = get_latest_health_data(user_id)
    if not health_data:
        health_data = {'heart_rate': 75, 'weight': 70.0, 'height': 170.0}

    # Save preferences
    pref_id = save_fitness_preferences(user_id, goal, days)

    # Delete old program
    existing = get_user_program(user_id)
    if existing:
        delete_user_program(user_id)

    # Generate new program
    preferences = FitnessPreferences(goal, days, "monthly")
    ai = AIEngine()
    program = ai.generate_and_save_program(
        user_id,
        preferences,
        health_data,
        pref_id,
        health_data.get('sync_id')
    )

    return jsonify({
        'success': True,
        'message': f'New {days}-day {goal} program generated for 4 weeks!'
    }), 200

# ════════════════════════════════════════
#  HISTORY ROUTE
# ════════════════════════════════════════
@app.route('/api/history', methods=['GET'])
def api_get_history():
    """Get user's completed workout history."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    history = get_user_workout_history(session['user_id'])
    return jsonify({'success': True, 'history': history}), 200


# ════════════════════════════════════════
#  PROFILE ROUTE
# ════════════════════════════════════════

@app.route('/api/profile', methods=['GET'])
def api_get_profile():
    """Get current user's profile info."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return jsonify({'success': False, 'message': 'User not found.'}), 404

    return jsonify({
        'success': True,
        'user': {
            'user_id': user_data['user_id'],
            'email':   user_data['email'],
            'phone':   user_data['phone_number']
        }
    }), 200


@app.route('/api/profile/health', methods=['PUT'])
def api_update_health():
    """
    Update user's health data (manual or PDF).
    Also saves body measurements when PDF is uploaded.
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    user_id = session['user_id']

    # Get values from form (these are the final values after user edits)
    heart_rate = request.form.get('heart_rate')
    weight = request.form.get('weight')
    height = request.form.get('height')

    # Check if PDF file is uploaded (for additional measurements only)
    pdf_file = request.files.get('pdf_file')
    extra_measurements = {}

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            pdf_file.save(tmp.name)
            tmp_path = tmp.name

        fetcher = HealthDataFetcher()
        extracted = fetcher.fetch_health_data_from_pdf(tmp_path)
        if extracted:
            # If user didn't provide values manually, use extracted ones
            if not heart_rate:
                heart_rate = extracted.get('heart_rate')
            if not weight:
                weight = extracted.get('weight')
            if not height:
                height = extracted.get('height')

            # Store extra measurements for body tracking
            extra_measurements = {
                'chest': extracted.get('chest'),
                'waist': extracted.get('waist'),
                'hips': extracted.get('hips')
            }

        try:
            os.unlink(tmp_path)
        except:
            pass

    # Validate and convert values
    try:
        heart_rate = int(heart_rate) if heart_rate else 75
        weight = float(weight) if weight else 70.0
        height = float(height) if height else 170.0
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid numeric values.'}), 400

    # Save to ENabizSync table
    sync_id = save_health_data(user_id, heart_rate, weight, height)

    # Save body measurement
    from database.db_manager import save_body_measurement
    save_body_measurement(
        user_id=user_id,
        weight=weight,
        chest=extra_measurements.get('chest'),
        waist=extra_measurements.get('waist'),
        hips=extra_measurements.get('hips'),
        notes="Updated from profile" + (" (PDF data)" if pdf_file else " (manual entry)")
    )

    return jsonify({
        'success': True,
        'message': 'Health data updated successfully!',
        'data': {
            'heart_rate': heart_rate,
            'weight': weight,
            'height': height
        }
    }), 200
# ════════════════════════════════════════
#  AGENT ROUTES
# ════════════════════════════════════════

@app.route('/api/agent/reply', methods=['POST'])
def api_agent_reply():
    """
    Submit user's reply to an agent prompt.
    Body: { prompt_id, reply }
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    data      = request.get_json()
    prompt_id = data.get('prompt_id')
    reply     = data.get('reply', '').strip()

    if not prompt_id or not reply:
        return jsonify({'success': False, 'message': 'prompt_id and reply are required.'}), 400

    agent = AgentAI()
    agent.receive_user_reply(prompt_id, reply)

    return jsonify({'success': True}), 200


@app.route('/api/agent/engagement', methods=['GET'])
def api_agent_engagement():
    """Get user's engagement stats."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    agent = AgentAI()
    stats = agent.check_engagement(session['user_id'])
    return jsonify({'success': True, 'stats': stats}), 200


# ════════════════════════════════════════
#  BODY MEASUREMENTS ROUTES
# ════════════════════════════════════════

@app.route('/api/measurements', methods=['POST'])
def api_save_measurement():
    """
    Save body measurement.
    Body: { weight, chest, waist, hips, arms, thighs, notes }
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    data = request.get_json()
    user_id = session['user_id']

    weight = data.get('weight')
    if not weight:
        return jsonify({'success': False, 'message': 'Weight is required.'}), 400

    measurement_id = save_body_measurement(
        user_id=user_id,
        weight=float(weight),
        chest=float(data.get('chest')) if data.get('chest') else None,
        waist=float(data.get('waist')) if data.get('waist') else None,
        hips=float(data.get('hips')) if data.get('hips') else None,
        arms=float(data.get('arms')) if data.get('arms') else None,
        thighs=float(data.get('thighs')) if data.get('thighs') else None,
        notes=data.get('notes', '')
    )

    return jsonify({
        'success': True,
        'message': 'Measurement saved!',
        'measurement_id': measurement_id
    }), 201

@app.route('/measurements')
def measurements_page():
    """Body measurements tracking page."""
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('measurements.html')

@app.route('/api/measurements', methods=['GET'])
def api_get_measurements():
    """Get user's measurement history."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    user_id = session['user_id']
    measurements = get_user_measurements(user_id)

    return jsonify({'success': True, 'data': measurements}), 200


@app.route('/api/measurements/progress', methods=['GET'])
def api_measurement_progress():
    """Get all measurements progress for charts."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    user_id = session['user_id']
    measurements = get_user_measurements(user_id)

    # Format ALL measurements for chart (not just weight)
    formatted_data = []
    for item in reversed(measurements):
        # Format date properly
        raw_date = item['recorded_date']
        if hasattr(raw_date, 'strftime'):
            formatted_date = raw_date.strftime('%Y-%m-%d')
        else:
            formatted_date = str(raw_date)[:10]  # Take first 10 chars

        formatted_data.append({
            'weight': float(item['weight']) if item.get('weight') else None,
            'chest': float(item['chest']) if item.get('chest') else None,
            'waist': float(item['waist']) if item.get('waist') else None,
            'hips': float(item['hips']) if item.get('hips') else None,
            'arms': float(item['arms']) if item.get('arms') else None,
            'thighs': float(item['thighs']) if item.get('thighs') else None,
            'recorded_date': formatted_date
        })

    # Get latest health data for BMI
    health = get_latest_health_data(user_id)
    latest_meas = get_latest_measurement(user_id)

    summary = None
    if health and latest_meas and len(measurements) > 0:
        tracker = BodyTracker()
        summary = tracker.get_progress_summary(list(reversed(measurements)), float(health.get('height', 170)))

    return jsonify({
        'success': True,
        'measurements': formatted_data,  # ✅ All measurements
        'summary': summary
    }), 200

# ════════════════════════════════════════
#  REPORT ROUTES
# ════════════════════════════════════════

@app.route('/api/report/generate', methods=['POST'])
def api_generate_report():
    """
    Generate a PDF progress report.
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    user_id = session['user_id']
    user_data = get_user_by_id(user_id)

    # Get program data
    ai = AIEngine()
    program_data = ai.get_program_with_progress(user_id)

    # Get measurements
    measurements = get_user_measurements(user_id)

    # Generate report
    generator = ReportGenerator(
        user_data={'email': user_data['email'], 'phone': user_data['phone_number']},
        program_data=program_data,
        measurements=measurements
    )

    report_path = generator.generate()

    # Return file for download
    from flask import send_file
    return send_file(report_path, as_attachment=True, download_name='fitness_report.pdf')


# ==================== NEW WORKOUT SYSTEM ====================

@app.route('/api/workout/start-session', methods=['POST'])
def api_start_workout_session():
    """
    Start a workout session for a specific day.
    Returns exercises with which ones have questions.
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    data = request.get_json()
    workout_id = data.get('workout_id')

    if not workout_id:
        return jsonify({'success': False, 'message': 'workout_id is required.'}), 400

    from database.db_manager import get_workout_by_id, get_exercises_by_workout

    workout = get_workout_by_id(workout_id)
    if not workout:
        return jsonify({'success': False, 'message': 'Workout not found.'}), 404

    if workout.get('completed'):
        return jsonify({'success': False, 'message': 'Workout already completed.'}), 400

    # Get exercises for this workout
    exercises = get_exercises_by_workout(workout_id)
    exercise_names = [ex['exercise_name'] for ex in exercises]
    total_exercises = len(exercise_names)

    # Randomly select which exercises will have questions (exactly 3)
    question_indices = WorkoutSession.select_random_questions(total_exercises, 3)

    # Create session data
    session_id = f"ws_{session['user_id']}_{workout_id}_{int(datetime.now().timestamp())}"

    # Prepare exercises with question info
    exercises_with_questions = []
    questions_list = []

    for idx, ex_name in enumerate(exercise_names):
        has_question = idx in question_indices
        question_data = None

        if has_question:
            question_data = WorkoutSession.get_random_question()
            questions_list.append({
                "exercise_index": idx,
                "exercise_name": ex_name,
                "question": question_data["question"],
                "options": question_data["options"],
                "correct_answer": question_data["correct"]
            })

        exercises_with_questions.append({
            "index": idx,
            "name": ex_name,
            "duration_seconds": 10,
            "has_question": has_question,
            "question": question_data["question"] if has_question else None,
            "options": question_data["options"] if has_question else None
        })

    # Store session in memory
    if not hasattr(app, 'workout_sessions'):
        app.workout_sessions = {}

    app.workout_sessions[session_id] = {
        "user_id": session['user_id'],
        "workout_id": workout_id,
        "day_number": workout['day_number'],
        "total_exercises": total_exercises,
        "exercise_names": exercise_names,
        "questions": questions_list,
        "answers": [],
        "completed_exercises": 0,
        "status": "in_progress",
        "created_at": datetime.now().isoformat()
    }

    return jsonify({
        'success': True,
        'session_id': session_id,
        'workout_id': workout_id,
        'day_number': workout['day_number'],
        'exercises': exercises_with_questions,
        'total_exercises': total_exercises,
        'questions_count': len(questions_list),
        'instructions': 'Complete each exercise. You have 10 seconds per exercise. Answer questions when they appear.'
    }), 200


@app.route('/api/workout/submit-answer', methods=['POST'])
def api_submit_answer():
    """
    Submit answer for a question during workout.
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    data = request.get_json()
    session_id = data.get('session_id')
    exercise_index = data.get('exercise_index')
    selected_answer = data.get('selected_answer')

    if not all([session_id, exercise_index is not None]):
        return jsonify({'success': False, 'message': 'Missing required fields.'}), 400

    if not hasattr(app, 'workout_sessions') or session_id not in app.workout_sessions:
        return jsonify({'success': False, 'message': 'Invalid or expired session.'}), 400

    workout_session = app.workout_sessions[session_id]

    # Find the question for this exercise
    question_info = None
    for q in workout_session['questions']:
        if q['exercise_index'] == exercise_index:
            question_info = q
            break

    if not question_info:
        # No question for this exercise, just mark as completed
        workout_session['completed_exercises'] += 1
        return jsonify({'success': True, 'no_question': True}), 200

    # Check if answer is correct
    is_correct = (selected_answer == question_info['correct_answer']) if selected_answer else False

    # Store answer
    workout_session['answers'].append({
        'exercise_index': exercise_index,
        'exercise_name': question_info['exercise_name'],
        'selected_answer': selected_answer,
        'correct_answer': question_info['correct_answer'],
        'is_correct': is_correct
    })

    workout_session['completed_exercises'] += 1

    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'correct_answer': question_info['correct_answer'] if not is_correct else None
    }), 200


@app.route('/api/workout/complete-session', methods=['POST'])
def api_complete_session():
    """
    Complete workout session and evaluate questions.
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    data = request.get_json()
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'success': False, 'message': 'session_id is required.'}), 400

    if not hasattr(app, 'workout_sessions') or session_id not in app.workout_sessions:
        return jsonify({'success': False, 'message': 'Invalid or expired session.'}), 400

    workout_session = app.workout_sessions[session_id]

    # Calculate results
    total_questions = len(workout_session['questions'])
    correct_answers = sum(1 for a in workout_session['answers'] if a['is_correct'])

    evaluation = WorkoutSession.evaluate_session(correct_answers, total_questions)

    if evaluation['success']:
        # Mark workout as completed
        from database.db_manager import mark_workout_completed, save_workout_history
        from datetime import datetime

        completed_date = datetime.now()
        workout_id = workout_session['workout_id']

        mark_workout_completed(workout_id, completed_date)
        save_workout_history(workout_session['user_id'], workout_id, completed_date)

        workout_session['status'] = 'completed'
        workout_session['completed_at'] = datetime.now().isoformat()

        # Clean up old sessions
        app.workout_sessions.pop(session_id, None)

        return jsonify({
            'success': True,
            'workout_accepted': True,
            'evaluation': evaluation,
            'message': f'✅ Workout completed! You got {correct_answers}/{total_questions} correct!'
        }), 200
    else:
        # Workout failed - keep session for retry (but we delete to restart)
        app.workout_sessions.pop(session_id, None)

        return jsonify({
            'success': False,
            'workout_accepted': False,
            'evaluation': evaluation,
            'message': f'❌ Workout failed! You got {correct_answers}/{total_questions} correct. You need at least 2 correct to pass. Please restart the workout.'
        }), 200


@app.route('/api/workout/session-status', methods=['GET'])
def api_session_status():
    """Get current workout session status."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'success': False, 'message': 'session_id required.'}), 400

    if not hasattr(app, 'workout_sessions') or session_id not in app.workout_sessions:
        return jsonify({'success': False, 'message': 'Session not found.'}), 404

    workout_session = app.workout_sessions[session_id]

    return jsonify({
        'success': True,
        'session': {
            'status': workout_session['status'],
            'completed_exercises': workout_session['completed_exercises'],
            'total_exercises': workout_session['total_exercises'],
            'answers_count': len(workout_session['answers']),
            'total_questions': len(workout_session['questions'])
        }
    }), 200


@app.route('/api/program/check-monthly-update', methods=['GET'])
def check_monthly_update():
    """
    Check if user needs to update measurements (monthly reminder).
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    user_id = session['user_id']
    program = get_user_program(user_id)

    if not program:
        return jsonify({'success': False, 'message': 'No program found'}), 404

    from datetime import datetime, timedelta
    start_date = program['start_date']
    days_since_start = (datetime.now().date() - start_date).days

    # Check if it's time for monthly update (every 30 days)
    needs_update = days_since_start >= 30
    next_update_days = max(0, 30 - days_since_start)

    # Get latest measurements
    latest_meas = get_latest_measurement(user_id)

    return jsonify({
        'success': True,
        'days_since_start': days_since_start,
        'needs_monthly_update': needs_update,
        'next_update_in_days': next_update_days,
        'latest_measurement': latest_meas
    }), 200


@app.route('/api/profile/extract-pdf', methods=['POST'])
def api_extract_pdf():
    """
    Extract health data from PDF and return without saving.
    Allows user to review and edit before saving.
    """
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    pdf_file = request.files.get('pdf_file')
    if not pdf_file or not pdf_file.filename.endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Please upload a valid PDF file.'}), 400

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        fetcher = HealthDataFetcher()
        extracted = fetcher.fetch_health_data_from_pdf(tmp_path)

        if extracted:
            # Prepare response without saving anything
            response_data = {
                'heart_rate': extracted.get('heart_rate'),
                'weight': extracted.get('weight'),
                'height': extracted.get('height'),
                'chest': extracted.get('chest'),
                'waist': extracted.get('waist'),
                'hips': extracted.get('hips')
            }
            return jsonify({'success': True, 'data': response_data}), 200
        else:
            return jsonify(
                {'success': False, 'message': 'Could not extract data from PDF. Please enter manually.'}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing PDF: {str(e)}'}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


@app.route('/api/profile/health-data', methods=['GET'])
def api_get_health_data():
    """Get user's current health data."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    user_id = session['user_id']
    health_data = get_latest_health_data(user_id)

    if health_data:
        return jsonify({'success': True, 'data': health_data}), 200
    return jsonify({'success': True, 'data': None}), 200


# ==================== SETUP ROUTES ====================

@app.route('/setup')
def setup():
    if not session.get('authenticated'):
        return redirect(url_for('index'))

    return render_template('setup.html')


@app.route('/api/pdf/extract', methods=['POST'])
def api_extract_pdf_data():
    """Extract data from PDF including age."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    pdf_file = request.files.get('pdf_file')
    if not pdf_file or not pdf_file.filename.endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Please upload a valid PDF file.'}), 400

    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        from models.health_data_fetcher import HealthDataFetcher
        fetcher = HealthDataFetcher()
        extracted = fetcher.fetch_health_data_from_pdf(tmp_path)

        if extracted:
            # ✅ Ensure age is included in response
            return jsonify({
                'success': True,
                'data': {
                    'heart_rate': extracted.get('heart_rate'),
                    'weight': extracted.get('weight'),
                    'height': extracted.get('height'),
                    'age': extracted.get('age'),
                    'chest': extracted.get('chest'),
                    'waist': extracted.get('waist'),
                    'hips': extracted.get('hips'),
                    'arms': extracted.get('arms'),
                    'thighs': extracted.get('thighs'),
                    'name': extracted.get('name'),
                    'date': extracted.get('date')
                }
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Could not extract data from PDF.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass

@app.route('/api/program/generate-from-setup', methods=['POST'])
def api_generate_from_setup():
    """Generate program from setup page with all data."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    user_id = session['user_id']
    goal = request.form.get('goal')
    days = int(request.form.get('days', 0))

    # Health data
    heart_rate = int(request.form.get('heart_rate', 75))
    weight = float(request.form.get('weight', 70))
    height = float(request.form.get('height', 170))
    age = request.form.get('age')

    # Body measurements
    chest = request.form.get('chest')
    waist = request.form.get('waist')
    hips = request.form.get('hips')
    arms = request.form.get('arms')
    thighs = request.form.get('thighs')

    # Save health data
    from database.db_manager import save_health_data, save_fitness_preferences, save_body_measurement, update_user_age
    sync_id = save_health_data(user_id, heart_rate, weight, height)

    # Update age if provided
    if age:
        update_user_age(user_id, int(age))

    # Save body measurement
    save_body_measurement(
        user_id=user_id,
        weight=weight,
        chest=float(chest) if chest else None,
        waist=float(waist) if waist else None,
        hips=float(hips) if hips else None,
        arms=float(arms) if arms else None,
        thighs=float(thighs) if thighs else None,
        notes="Initial setup measurement"
    )

    # Save preferences
    pref_id = save_fitness_preferences(user_id, goal, days)

    # Generate program
    from models.fitness_preferences import FitnessPreferences
    from models.ai_engine import AIEngine
    prefs = FitnessPreferences(goal, days, "monthly")
    ai = AIEngine()
    ai.generate_and_save_program(user_id, prefs, {'heart_rate': heart_rate, 'weight': weight, 'height': height},
                                 pref_id, sync_id)

    return jsonify({'success': True, 'message': f'Program generated for {days} days/week with goal: {goal}!'}), 200


# ==================== PROFILE ROUTES ====================

@app.route('/api/profile/info', methods=['GET'])
def api_profile_info():
    """Get user profile info including age."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    from database.db_manager import get_user_by_id, get_user_age
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    age = get_user_age(user_id)  # ← تأكد من وجود هذه الدالة

    return jsonify({
        'success': True,
        'data': {
            'email': user['email'],
            'phone': user['phone_number'],
            'age': age
        }
    }), 200


@app.route('/api/profile/age', methods=['PUT'])
def api_update_age():
    """Update user age."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided.'}), 400

    age = data.get('age')

    if age is None:
        return jsonify({'success': False, 'message': 'Age is required.'}), 400

    try:
        age = int(age)
        if age < 10 or age > 120:
            return jsonify({'success': False, 'message': 'Age must be between 10 and 120.'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid age value.'}), 400

    from database.db_manager import update_user_age
    update_user_age(session['user_id'], age)

    return jsonify({'success': True, 'message': 'Age updated successfully.'}), 200

@app.route('/api/profile/password', methods=['PUT'])
def api_change_password():
    """Change user password."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    data = request.get_json()
    new_password = data.get('password')

    if not new_password or len(new_password) < 3:
        return jsonify({'success': False, 'message': 'Password must be at least 3 characters.'}), 400

    from database.db_manager import update_user_password
    update_user_password(session['user_id'], new_password)

    return jsonify({'success': True, 'message': 'Password changed.'}), 200


@app.route('/api/measurements/latest', methods=['GET'])
def api_get_latest_measurement():
    """Get user's latest measurement."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    from database.db_manager import get_latest_measurement
    user_id = session['user_id']
    measurement = get_latest_measurement(user_id)

    return jsonify({'success': True, 'data': measurement}), 200
@app.route('/api/profile/preferences', methods=['GET'])
def api_get_preferences():
    """Get user's current fitness preferences."""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 401

    from database.db_manager import get_preferences_by_user
    user_id = session['user_id']
    prefs = get_preferences_by_user(user_id)

    return jsonify({'success': True, 'data': prefs}), 200
if __name__ == '__main__':
    app.run(debug=True, port=5000)

