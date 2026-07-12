// ==================== Utility Functions ====================

function showMessage(message, type = 'success') {
    const msg = document.getElementById('message');
    if (!msg) return;
    msg.textContent = message;
    msg.className = `message ${type}`;
    setTimeout(() => msg.className = 'message', 5000);
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `message ${type}`;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.maxWidth = '300px';
    toast.style.zIndex = '2000';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// ==================== API Service ====================

class APIService {
    constructor() {
        this.baseUrl = '';
    }

    async request(url, method = 'GET', body = null) {
        const options = {
            method,
            credentials: 'same-origin',
            headers: {}
        };

        if (body) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, options);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('API Error:', error);
            return { success: false, message: 'Network error.' };
        }
    }

    get(url) { return this.request(url, 'GET'); }
    post(url, body) { return this.request(url, 'POST', body); }
    put(url, body) { return this.request(url, 'PUT', body); }
}

const api = new APIService();

// ==================== WORKOUT SESSION FUNCTIONS ====================

let currentSession = null;
let currentExerciseIndex = 0;
let timerInterval = null;

async function startWorkoutSession(workoutId) {
    showWorkoutModal();

    try {
        const result = await api.post('/api/workout/start-session', { workout_id: workoutId });

        if (result.success) {
            currentSession = result;
            currentExerciseIndex = 0;
            showNextExercise();
        } else {
            alert(result.message || 'Failed to start workout');
            closeWorkoutModal();
        }
    } catch (error) {
        console.error('Error starting session:', error);
        alert('Failed to start workout session.');
        closeWorkoutModal();
    }
}

function showWorkoutModal() {
    const modal = document.getElementById('workout-modal');
    if (modal) modal.style.display = 'flex';
}

function closeWorkoutModal() {
    if (timerInterval) clearInterval(timerInterval);
    const modal = document.getElementById('workout-modal');
    if (modal) modal.style.display = 'none';
    currentSession = null;
    currentExerciseIndex = 0;
}

function showNextExercise() {
    if (timerInterval) clearInterval(timerInterval);

    const exercises = currentSession.exercises;

    if (currentExerciseIndex >= exercises.length) {
        completeWorkoutSession();
        return;
    }

    const exercise = exercises[currentExerciseIndex];
    renderExerciseUI(exercise);
}

function renderExerciseUI(exercise) {
    const container = document.getElementById('workout-session-container');
    if (!container) return;

    let timeLeft = exercise.duration_seconds;
    let exerciseCompleted = false;
    let questionAnswered = false;

    container.innerHTML = `
        <div class="exercise-card">
            <div class="exercise-name">${exercise.name}</div>
            <div class="timer" id="exercise-timer">${timeLeft}s</div>
            <div class="progress-bar" style="margin: 10px 0;">
                <div class="progress-fill" id="timer-progress" style="width: 100%;"></div>
            </div>
            <p>💪 Perform this exercise now!</p>
            <div id="question-section" style="display: none;">
                ${exercise.has_question ? `
                    <div class="question-box">
                        <div class="question-text">❓ ${exercise.question}</div>
                        <div id="options-container">
                            ${exercise.options.map(opt => `
                                <button class="option-btn" onclick="submitAnswerForCurrentExercise('${opt.replace(/'/g, "\\'")}')">${opt}</button>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
            <button class="next-btn" id="next-btn" onclick="nextExercise()" style="display: none;">Next Exercise →</button>
        </div>
    `;

    const timerElement = document.getElementById('exercise-timer');
    const progressElement = document.getElementById('timer-progress');
    const questionSection = document.getElementById('question-section');

    // Timer for exercise performance (10 seconds)
    timerInterval = setInterval(() => {
        timeLeft--;
        if (timerElement) timerElement.textContent = `${timeLeft}s`;
        if (progressElement) progressElement.style.width = `${(timeLeft / exercise.duration_seconds) * 100}%`;

        if (timeLeft <= 0 && !exerciseCompleted) {
            clearInterval(timerInterval);
            exerciseCompleted = true;

            // Timer finished - show question (if any)
            if (exercise.has_question && questionSection) {
                questionSection.style.display = 'block';
            } else {
                // No question, show next button
                const nextBtn = document.getElementById('next-btn');
                if (nextBtn) nextBtn.style.display = 'block';
            }
        }
    }, 1000);
}
// Global variable to store current exercise for answer submission
let currentAnswerExercise = null;

async function submitAnswerForCurrentExercise(selectedAnswer) {
    if (!currentSession) return;

    // Disable all option buttons
    document.querySelectorAll('.option-btn').forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = '0.6';
    });

    try {
        const result = await api.post('/api/workout/submit-answer', {
            session_id: currentSession.session_id,
            exercise_index: currentExerciseIndex,
            selected_answer: selectedAnswer
        });

        if (result.success) {
            const feedbackDiv = document.createElement('div');
            feedbackDiv.style.marginTop = '10px';
            feedbackDiv.style.padding = '10px';
            feedbackDiv.style.borderRadius = '8px';
            feedbackDiv.style.backgroundColor = result.is_correct ? '#e8f5e9' : '#ffebee';
            feedbackDiv.style.color = result.is_correct ? '#2e7d32' : '#c62828';
            feedbackDiv.textContent = result.is_correct ? '✅ Correct!' : `❌ Wrong! Correct answer: ${result.correct_answer}`;

            const optionsContainer = document.getElementById('options-container');
            if (optionsContainer) optionsContainer.appendChild(feedbackDiv);
        }

        // Show next button after answer
        const nextBtn = document.getElementById('next-btn');
        if (nextBtn) nextBtn.style.display = 'block';

    } catch (error) {
        console.error('Error submitting answer:', error);
        const nextBtn = document.getElementById('next-btn');
        if (nextBtn) nextBtn.style.display = 'block';
    }
}
window.nextExercise = () => {
    if (timerInterval) clearInterval(timerInterval);
    currentExerciseIndex++;
    showNextExercise();
};
async function completeWorkoutSession() {
    const container = document.getElementById('workout-session-container');
    if (!container) return;

    container.innerHTML = '<div class="result-box"><div class="loading-spinner"></div><p>Analyzing your results...</p></div>';

    try {
        const result = await api.post('/api/workout/complete-session', {
            session_id: currentSession.session_id
        });

        if (result.success) {
            container.innerHTML = `
                <div class="result-box">
                    <div class="result-success">✅ ${result.message}</div>
                    <button class="btn-primary" onclick="closeWorkoutModal(); location.reload();" style="margin-top: 20px;">Close</button>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div class="result-box">
                    <div class="result-fail">❌ ${result.message}</div>
                    <button class="btn-primary retry-btn" onclick="retryWorkout()" style="margin-top: 20px;">🔄 Try Again</button>
                    <button class="btn-secondary" onclick="closeWorkoutModal()" style="margin-top: 10px;">Close</button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error completing session:', error);
        container.innerHTML = `<div class="result-box"><div class="result-fail">❌ Error. Please try again.</div><button class="btn-primary" onclick="closeWorkoutModal()">Close</button></div>`;
    }
}

async function retryWorkout() {
    const workoutId = currentSession.workout_id;
    closeWorkoutModal();
    setTimeout(() => startWorkoutSession(workoutId), 500);
}

// Make functions global
window.startWorkoutSession = startWorkoutSession;
window.closeWorkoutModal = closeWorkoutModal;
window.retryWorkout = retryWorkout;

// ==================== Auth Manager ====================

class AuthManager {
    constructor() {
        this.loginForm = document.getElementById('login-form');
        this.registerForm = document.getElementById('register-form');
        this.init();
    }

    init() {
        if (this.loginForm) {
            this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        if (this.registerForm) {
            this.registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        const result = await api.post('/api/auth/login', { email, password });

        if (result.success) {
            showMessage('Login successful! Redirecting...', 'success');
            setTimeout(() => window.location.href = '/dashboard', 1000);
        } else {
            showMessage(result.message || 'Login failed', 'error');
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        const phone = document.getElementById('reg-phone').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;

        const result = await api.post('/api/auth/register', {
            phone_number: phone,
            email: email,
            password: password
        });

        if (result.success) {
            document.getElementById('register-form').classList.add('hidden');
            document.getElementById('reg-verify').classList.remove('hidden');
            showMessage('Verification code sent!', 'success');
        } else {
            showMessage(result.message || 'Registration failed', 'error');
        }
    }

    async verifyEmail() {
        const email = document.getElementById('reg-email').value;
        const code = document.getElementById('reg-code').value;
        const btn = document.getElementById('verify-email-btn');
        const loading = document.getElementById('verify-loading');

        if (!code || code.length < 6) {
            showMessage('Please enter the 6-digit verification code.', 'error');
            return;
        }

        btn.disabled = true;
        btn.textContent = 'Verifying...';
        if (loading) loading.classList.remove('hidden');

        try {
            const result = await api.post('/api/auth/verify-email', { email, code });

            if (result.success) {
                showMessage('Email verified! Redirecting...', 'success');
                if (result.reg_token) {
                    localStorage.setItem('reg_token', result.reg_token);
                }
                setTimeout(() => window.location.href = '/profile', 1500);
            } else {
                showMessage(result.message || 'Invalid or expired code.', 'error');
                btn.disabled = false;
                btn.textContent = 'Verify & Continue';
                if (loading) loading.classList.add('hidden');
            }
        } catch (error) {
            showMessage('Connection error. Please try again.', 'error');
            btn.disabled = false;
            btn.textContent = 'Verify & Continue';
            if (loading) loading.classList.add('hidden');
        }
    }
}

// ==================== Dashboard Manager ====================

class DashboardManager {
    constructor() {
        this.init();
    }

    init() {
        if (document.getElementById('dashboard-content')) {
            this.loadDashboard();
        }
    }

    async loadDashboard() {
        try {
            const result = await api.get('/api/program');

            if (result.success) {
                document.getElementById('dashboard-loading')?.classList.add('hidden');
                document.getElementById('dashboard-content')?.classList.remove('hidden');

                const data = result.data;
                this.renderProgress(data.progress);
                this.renderNextWorkout(data.next_workout);
                this.renderWeeklySummary(data.program);
            } else {
                document.getElementById('dashboard-loading').innerHTML = '<p>No active program. Go to Profile to create one!</p>';
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
        }
    }

    renderProgress(progress) {
        const progressText = document.getElementById('progress-text');
        const progressPercent = document.getElementById('progress-percent');
        const progressFill = document.getElementById('progress-fill');

        if (progressText) progressText.textContent = `${progress.completed}/${progress.total} days completed`;
        if (progressPercent) progressPercent.textContent = `${progress.percentage}%`;
        if (progressFill) progressFill.style.width = `${progress.percentage}%`;
    }

    renderNextWorkout(nextWorkout) {
        const container = document.getElementById('next-workout-info');
        if (!container) return;

        if (nextWorkout) {
            container.innerHTML = `
                <p style="font-size: 2.5em; font-weight: bold; color: #667eea; text-align: center;">Day ${nextWorkout.day}</p>
                <button onclick="startWorkoutSession('${nextWorkout.workout_id}')" class="btn-primary" style="margin-top: 15px;">🚀 Start Workout</button>
            `;
        } else {
            container.innerHTML = '<p style="text-align: center; font-size: 1.2em;">🎉 All workouts completed! 🎉</p>';
        }
    }

    renderWeeklySummary(program) {
        const container = document.getElementById('workouts-list');
        if (!container || !program.weeks) return;

        let html = '';
        program.weeks.forEach(week => {
            html += `
                <div class="week-card" style="margin-bottom: 15px;">
                    <div class="week-header">
                        <div class="week-title">Week ${week.week_number}</div>
                        <div class="week-progress">${week.completed}/${week.total} completed</div>
                    </div>
                    <div style="padding: 15px; display: flex; flex-wrap: wrap; gap: 10px;">
                        ${week.workouts.map(w => `
                            <div style="flex: 1; min-width: 80px; text-align: center; padding: 10px; background: ${w.completed ? '#e8f5e9' : '#fff3e0'}; border-radius: 10px;">
                                <div style="font-weight: bold;">Day ${w.day}</div>
                                <div>${w.completed ? '✅' : '⏳'}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }
}

// ==================== History Manager ====================

class HistoryManager {
    constructor() {
        this.init();
    }

    init() {
        if (document.getElementById('history-content')) {
            this.loadHistory();
        }
    }

    async loadHistory() {
        try {
            const result = await api.get('/api/history');

            document.getElementById('history-loading')?.classList.add('hidden');
            document.getElementById('history-content')?.classList.remove('hidden');

            if (result.success && result.history && result.history.length > 0) {
                const historyHtml = result.history.map(h => `
                    <div class="history-item">
                        <span class="history-day">✅ Day ${h.day_number}</span>
                        <span class="history-date">${formatDate(h.completed_date)}</span>
                    </div>
                `).join('');

                const historyList = document.getElementById('history-list');
                if (historyList) historyList.innerHTML = historyHtml;
                document.getElementById('history-empty')?.classList.add('hidden');
            } else {
                document.getElementById('history-empty')?.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }
}

// ==================== Profile Manager ====================

class ProfileManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupHealthForm();
        this.setupPrefsForm();
    }

    setupHealthForm() {
        const healthForm = document.getElementById('health-form');
        if (!healthForm) return;

        healthForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const pdfFile = document.getElementById('pdf-file')?.files[0];
            const heartRate = document.getElementById('heart-rate')?.value;
            const weight = document.getElementById('weight')?.value;
            const height = document.getElementById('height')?.value;

            const formData = new FormData();
            if (pdfFile) formData.append('pdf_file', pdfFile);
            if (heartRate) formData.append('heart_rate', heartRate);
            if (weight) formData.append('weight', weight);
            if (height) formData.append('height', height);

            try {
                const response = await fetch('/api/profile/health', {
                    method: 'PUT',
                    credentials: 'include',
                    body: formData
                });

                const result = await response.json();
                const msg = document.getElementById('profile-message');

                if (result.success) {
                    msg.textContent = '✅ Health data updated successfully!';
                    msg.className = 'message success';
                    setTimeout(() => msg.className = 'message', 3000);
                } else {
                    msg.textContent = result.message || 'Update failed';
                    msg.className = 'message error';
                }
            } catch (error) {
                const msg = document.getElementById('profile-message');
                msg.textContent = 'Network error. Please try again.';
                msg.className = 'message error';
            }
        });
    }

    setupPrefsForm() {
        const prefsForm = document.getElementById('prefs-form');
        if (!prefsForm) return;

        prefsForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const goal = document.getElementById('goal')?.value;
            const days = document.getElementById('days')?.value;

            if (!goal || !days) {
                showMessage('Please fill all fields', 'error');
                return;
            }

            const result = await api.post('/api/program/generate', { goal, days: parseInt(days) });

            const msg = document.getElementById('profile-message');
            if (result.success) {
                msg.textContent = '✅ Preferences updated and program regenerated!';
                msg.className = 'message success';
                setTimeout(() => window.location.href = '/program', 1500);
            } else {
                msg.textContent = result.message || 'Update failed';
                msg.className = 'message error';
            }
        });
    }
}

// ==================== Measurements Manager ====================

class MeasurementsManager {
    constructor() {
        this.chart = null;
        this.init();
    }

    init() {
        if (document.getElementById('measurement-form')) {
            this.setupForm();
            this.loadMeasurements();
        }
    }

    setupForm() {
        const form = document.getElementById('measurement-form');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const data = {
                weight: parseFloat(document.getElementById('meas-weight').value),
                chest: document.getElementById('meas-chest')?.value || null,
                waist: document.getElementById('meas-waist')?.value || null,
                hips: document.getElementById('meas-hips')?.value || null,
                arms: document.getElementById('meas-arms')?.value || null,
                thighs: document.getElementById('meas-thighs')?.value || null,
                notes: document.getElementById('meas-notes')?.value || null
            };

            const result = await api.post('/api/measurements', data);
            const msg = document.getElementById('meas-message');

            if (result.success) {
                msg.textContent = '✅ Measurement saved!';
                msg.className = 'message success';
                form.reset();
                this.loadMeasurements();
                setTimeout(() => msg.className = 'message', 3000);
            } else {
                msg.textContent = '❌ ' + (result.message || 'Error saving measurement');
                msg.className = 'message error';
            }
        });
    }

    async loadMeasurements() {
        try {
            const progressResult = await api.get('/api/measurements/progress');

            if (progressResult.success && progressResult.summary) {
                this.renderSummary(progressResult.summary);
            }

            if (progressResult.success && progressResult.measurements && progressResult.measurements.length > 0) {
                document.getElementById('no-data-message')?.style.setProperty('display', 'none');
                this.drawChart(progressResult.measurements);
            } else {
                document.getElementById('no-data-message')?.style.setProperty('display', 'block');
            }
        } catch (error) {
            console.error('Error loading progress:', error);
        }

        try {
            const historyResult = await api.get('/api/measurements');
            const list = document.getElementById('measurements-list');

            if (historyResult.success && historyResult.data && historyResult.data.length > 0) {
                list.innerHTML = historyResult.data.slice().reverse().map(m => `
                    <div class="history-item">
                        <span class="history-day">⚖️ ${m.weight} kg</span>
                        <span style="color:#999;">Waist: ${m.waist || '-'} | Chest: ${m.chest || '-'}</span>
                        <span class="history-date">${formatDate(m.recorded_date)}</span>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<p style="text-align:center; color:#999;">No measurements yet.</p>';
            }
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }

    renderSummary(summary) {
    const container = document.getElementById('progress-summary');
    if (!container) return;

    container.innerHTML = `
        <div class="form-row">
            <div style="flex:1; text-align:center; background:#f8f9fa; padding:15px; border-radius:12px;">
                <h3 style="color:#667eea; font-size:1.8em;">${summary.weight?.current || '0'} kg</h3>
                <p>Current Weight</p>
                <small>${summary.weight?.change?.direction === 'lost' ? `📉 Lost ${Math.abs(summary.weight.change.absolute_change)} kg` :
                          summary.weight?.change?.direction === 'gained' ? `📈 Gained ${summary.weight.change.absolute_change} kg` :
                          '➡️ Stable'}</small>
            </div>
            <div style="flex:1; text-align:center; background:#f8f9fa; padding:15px; border-radius:12px;">
                <h3 style="color:#667eea; font-size:1.8em;">${summary.bmi?.bmi || '0'}</h3>
                <p>BMI (${summary.bmi?.category || 'N/A'})</p>
            </div>
            <div style="flex:1; text-align:center; background:#f8f9fa; padding:15px; border-radius:12px;">
                <h3 style="color:#667eea; font-size:1.8em;">${summary.total_measurements || 0}</h3>
                <p>Total Measurements</p>
                <small>📅 ${formatDate(summary.first_date)} - ${formatDate(summary.latest_date)}</small>
            </div>
        </div>
        ${summary.waist_change ? `
        <div class="form-row" style="margin-top:15px;">
            <div style="flex:1; text-align:center;">
                <p>📏 Waist change: ${summary.waist_change > 0 ? `+${summary.waist_change}` : summary.waist_change} cm</p>
            </div>
        </div>
        ` : ''}
    `;
}

    drawChart(data) {
    const ctx = document.getElementById('measurements-chart')?.getContext('2d');
    if (!ctx) return;

    if (this.chart) this.chart.destroy();

    // Format dates
    const dates = data.map(d => {
        const dateStr = d.recorded_date;
        return dateStr.length > 10 ? dateStr.substring(0, 10) : dateStr;
    });

    const datasets = [];

    // Weight dataset (kg)
    const weights = data.map(d => d.weight);
    if (weights.some(w => w !== null && w !== undefined)) {
        datasets.push({
            label: 'Weight (kg)',
            data: weights,
            borderColor: '#667eea',
            backgroundColor: 'rgba(102, 126, 234, 0.1)',
            tension: 0.3,
            pointRadius: 5,
            pointHoverRadius: 7,
            fill: true,
            yAxisID: 'y'
        });
    }

    // Chest dataset (cm)
    const chests = data.map(d => d.chest);
    if (chests.some(c => c !== null && c !== undefined)) {
        datasets.push({
            label: 'Chest (cm)',
            data: chests,
            borderColor: '#e74c3c',
            backgroundColor: 'rgba(231, 76, 60, 0.1)',
            tension: 0.3,
            pointRadius: 4,
            fill: true,
            yAxisID: 'y'
        });
    }

    // Waist dataset (cm)
    const waists = data.map(d => d.waist);
    if (waists.some(w => w !== null && w !== undefined)) {
        datasets.push({
            label: 'Waist (cm)',
            data: waists,
            borderColor: '#2ecc71',
            backgroundColor: 'rgba(46, 204, 113, 0.1)',
            tension: 0.3,
            pointRadius: 4,
            fill: true,
            yAxisID: 'y'
        });
    }

    // Hips dataset (cm)
    const hips = data.map(d => d.hips);
    if (hips.some(h => h !== null && h !== undefined)) {
        datasets.push({
            label: 'Hips (cm)',
            data: hips,
            borderColor: '#f39c12',
            backgroundColor: 'rgba(243, 156, 18, 0.1)',
            tension: 0.3,
            pointRadius: 4,
            fill: true,
            yAxisID: 'y'
        });
    }

    // Arms dataset (cm)
    const arms = data.map(d => d.arms);
    if (arms.some(a => a !== null && a !== undefined)) {
        datasets.push({
            label: 'Arms (cm)',
            data: arms,
            borderColor: '#9b59b6',
            backgroundColor: 'rgba(155, 89, 182, 0.1)',
            tension: 0.3,
            pointRadius: 4,
            fill: true,
            yAxisID: 'y'
        });
    }

    // Thighs dataset (cm)
    const thighs = data.map(d => d.thighs);
    if (thighs.some(t => t !== null && t !== undefined)) {
        datasets.push({
            label: 'Thighs (cm)',
            data: thighs,
            borderColor: '#1abc9c',
            backgroundColor: 'rgba(26, 188, 156, 0.1)',
            tension: 0.3,
            pointRadius: 4,
            fill: true,
            yAxisID: 'y'
        });
    }

    // Create chart with all datasets
    this.chart = new Chart(ctx, {
        type: 'line',
        data: { labels: dates, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, padding: 15, font: { size: 11 } }
                },
                tooltip: { mode: 'index', intersect: false }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: { display: true, text: 'Measurement (kg / cm)', font: { weight: 'bold' } },
                    grid: { color: '#e0e0e0' }
                },
                x: {
                    title: { display: true, text: 'Date', font: { weight: 'bold' } },
                    ticks: { maxRotation: 45, minRotation: 45 }
                }
            }
        }
    });
}

    async generateReport() {
        try {
            const response = await fetch('/api/report/generate', {
                method: 'POST',
                credentials: 'include'
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'fitness_report.pdf';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                showToast('Report downloaded successfully!', 'success');
            } else {
                showToast('Error generating report', 'error');
            }
        } catch (error) {
            console.error('Report error:', error);
            showToast('Error generating report', 'error');
        }
    }
}
// ==================== Program Manager ====================

class ProgramManager {
    constructor() {
        this.currentWeek = 1;
        this.programData = null;
        this.init();
    }

    init() {
        if (document.getElementById('program-content')) {
            this.loadProgram();
        }
    }

    async loadProgram() {
        try {
            const result = await api.get('/api/program');

            if (result.success) {
                document.getElementById('program-loading')?.classList.add('hidden');
                document.getElementById('program-content')?.classList.remove('hidden');
                this.programData = result.data;
                this.renderProgram();
            } else {
                this.showEmptyState();
            }
        } catch (error) {
            console.error('Error loading program:', error);
            this.showError();
        }
    }

    renderProgram() {
        const data = this.programData;
        const program = data.program;
        this.renderHeader(program, data.progress);
        this.renderWeeksNavigation(program);
        this.renderCurrentWeek(program);
    }

    renderHeader(program, progress) {
        const headerHtml = `
            <div class="program-header">
                <h2>🏋️ ${program.program_id}</h2>
                <p>Started: ${program.formatted_date}</p>
                <div class="program-stats">
                    <div class="stat-card">
                        <div class="stat-number">${progress.completed}/${progress.total}</div>
                        <div class="stat-label">Workouts Completed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${progress.percentage}%</div>
                        <div class="stat-label">Overall Progress</div>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress.percentage}%">${progress.percentage}%</div>
                </div>
            </div>
        `;
        const existingHeader = document.getElementById('program-details');
        if (existingHeader) existingHeader.innerHTML = headerHtml;
    }

    renderWeeksNavigation(program) {
        if (!program.weeks || program.weeks.length === 0) return;

        const navHtml = `
            <div class="weeks-nav">
                ${program.weeks.map((week, index) => `
                    <button class="week-btn ${index + 1 === this.currentWeek ? 'active' : ''}"
                            onclick="programManager.switchWeek(${index + 1})">
                        Week ${week.week_number}
                        ${week.progress === 100 ? ' ✓' : ''}
                    </button>
                `).join('')}
            </div>
        `;
        const container = document.getElementById('program-details');
        if (container) {
            let navDiv = document.getElementById('weeks-nav');
            if (!navDiv) {
                navDiv = document.createElement('div');
                navDiv.id = 'weeks-nav';
                container.appendChild(navDiv);
            }
            navDiv.innerHTML = navHtml;
        }
    }

    renderCurrentWeek(program) {
        if (!program.weeks || program.weeks.length === 0) return;

        const currentWeekData = program.weeks[this.currentWeek - 1];
        if (!currentWeekData) return;

        const completedCount = currentWeekData.workouts.filter(w => w.completed).length;
        const weekProgress = (completedCount / currentWeekData.workouts.length) * 100;

        const weekHtml = `
            <div class="week-card">
                <div class="week-header">
                    <div class="week-title">📅 Week ${currentWeekData.week_number}</div>
                    <div class="week-progress">
                        ${completedCount}/${currentWeekData.workouts.length} Completed
                        <div class="progress-bar-small">
                            <div class="progress-fill-small" style="width: ${weekProgress}%"></div>
                        </div>
                    </div>
                </div>
                <div class="workouts-grid" id="workouts-grid-container">
                    ${currentWeekData.workouts.map(workout => this.renderWorkoutCard(workout)).join('')}
                </div>
            </div>
        `;
        const container = document.getElementById('workouts-grid');
        if (container) container.innerHTML = weekHtml;
    }

    renderWorkoutCard(workout) {
        const statusClass = workout.completed ? 'completed' : 'pending';
        const statusText = workout.completed ? 'Completed' : 'Pending';

        return `
            <div class="workout-card ${statusClass}" id="workout-${workout.workout_id}">
                <div class="workout-header" onclick="programManager.toggleWorkout('${workout.workout_id}')">
                    <div class="workout-day">
                        <span class="day-number">Day ${workout.day}</span>
                        <span class="day-badge ${statusClass}">${statusText}</span>
                    </div>
                    <div class="workout-expand-icon">▼</div>
                </div>
                <div class="workout-details">
                    <div class="exercises-list">
                        ${workout.exercises.map(ex => `<div class="exercise-item">💪 ${ex}</div>`).join('')}
                    </div>
                    ${workout.video_url ? `<a href="${workout.video_url}" target="_blank" class="video-link">📹 Watch Workout Video →</a>` : ''}
                </div>
            </div>
        `;
    }

    switchWeek(weekNumber) {
        this.currentWeek = weekNumber;
        this.renderWeeksNavigation(this.programData.program);
        this.renderCurrentWeek(this.programData.program);
    }

    toggleWorkout(workoutId) {
        const card = document.getElementById(`workout-${workoutId}`);
        if (card) card.classList.toggle('expanded');
    }

    showEmptyState() {
        const container = document.getElementById('program-content');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>📭 No active program found.</p>
                    <a href="/profile" class="btn-primary" style="display: inline-block; margin-top: 20px;">Go to Profile</a>
                </div>
            `;
        }
        document.getElementById('program-loading')?.classList.add('hidden');
    }

    showError() {
        const container = document.getElementById('program-content');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>❌ Error loading program.</p>
                    <button onclick="location.reload()" class="btn-primary">Retry</button>
                </div>
            `;
        }
        document.getElementById('program-loading')?.classList.add('hidden');
    }
}
// Make answer function global
window.submitAnswerForCurrentExercise = submitAnswerForCurrentExercise;
// ==================== Page Initialization ====================

let authManager, programManager, dashboardManager, historyManager, profileManager, measurementsManager;

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('login-form') || document.getElementById('register-form')) {
        authManager = new AuthManager();
        window.verifyEmail = () => authManager.verifyEmail();
    }

    if (document.getElementById('program-content')) {
        programManager = new ProgramManager();
        window.programManager = programManager;
    }

    if (document.getElementById('dashboard-content')) {
        dashboardManager = new DashboardManager();
        window.dashboardManager = dashboardManager;
    }

    if (document.getElementById('history-content')) {
        historyManager = new HistoryManager();
    }

    if (document.getElementById('health-form') || document.getElementById('prefs-form')) {
        profileManager = new ProfileManager();
    }

    if (document.getElementById('measurement-form')) {
        measurementsManager = new MeasurementsManager();
        window.generateReport = () => measurementsManager.generateReport();
    }
});

function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
    document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
}