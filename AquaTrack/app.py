from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'aquatrack_secret_encryption_key_2026'

# Database configuration using SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aquatrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ----------------------------------------
# DATABASE MODELS
# ----------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    logs = db.relationship('WaterLog', backref='user', lazy=True, cascade="all, delete-orphan")

class WaterLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    liters = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    activity = db.Column(db.String(50), default="General")

# Helper function to compute custom eco scores dynamically
def calculate_eco_metrics(user_logs):
    if not user_logs:
        return 0, 100, "Eco Rookie", "text-gray-400"
    
    total = sum(log.liters for log in user_logs)
    
    # Eco Score Calculation: Base 100, drops as consumption goes past sustainable baselines
    # Let's say a baseline allocation is 150 liters per record log
    avg_usage = total / len(user_logs)
    eco_score = max(0, min(100, int(100 - (avg_usage - 100) * 0.4)))
    
    # Tier assessment based on score
    if eco_score >= 85:
        tier, color = "Hydration Hero", "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
    elif eco_score >= 50:
        tier, color = "Water Saver", "text-sky-400 border-sky-500/30 bg-sky-500/10"
    else:
        tier, color = "Excessive Consumer", "text-rose-400 border-rose-500/30 bg-rose-500/10"
        
    return round(total, 1), eco_score, tier, color

# ----------------------------------------
# ROUTES & APPLICATION LOGIC
# ----------------------------------------

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_logs = WaterLog.query.filter_by(user_id=session['user_id']).order_by(WaterLog.timestamp.desc()).all()
    total_usage, eco_score, tier, tier_color = calculate_eco_metrics(user_logs)
    
    return render_template('index.html', 
                           username=session['username'], 
                           logs=user_logs, 
                           total_usage=total_usage, 
                           eco_score=eco_score,
                           tier=tier,
                           tier_color=tier_color)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Try logging in!', 'error')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
            
        flash('Invalid username or password.', 'error')
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/log-water', methods=['POST'])
def log_water():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        liters = float(request.form.get('liters'))
        activity = request.form.get('activity', 'General')
        if liters <= 0:
            raise ValueError
    except (TypeError, ValueError):
        flash('Please enter a valid, positive consumption number.', 'error')
        return redirect(url_for('index'))
        
    new_log = WaterLog(user_id=session['user_id'], liters=liters, activity=activity)
    db.session.add(new_log)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete-log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    log = WaterLog.query.get_or_404(log_id)
    if log.user_id == session['user_id']:
        db.session.delete(log)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/clear-history', methods=['POST'])
def clear_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    WaterLog.query.filter_by(user_id=session['user_id']).delete()
    db.session.commit()
    flash('All logs have been completely cleared.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Build database structural maps tables safely
    if __name__ == '__main__':
        with app.app_context():
            db.create_all()
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
