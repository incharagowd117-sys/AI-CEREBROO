from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, User

auth = Blueprint('auth', __name__)

# ── Register ──────────────────────────────────────────────
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Try another.', 'error')
            return render_template('register.html')
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['username'] = user.username
        session.permanent = True
        return redirect(url_for('index'))
    return render_template('register.html')

# ── Login ─────────────────────────────────────────────────
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Incorrect username or password.', 'error')
            return render_template('login.html')
        session['user_id'] = user.id
        session['username'] = user.username
        session.permanent = True
        return redirect(url_for('index'))
    return render_template('login.html')

# ── Logout ────────────────────────────────────────────────
@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))