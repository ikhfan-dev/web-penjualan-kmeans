from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from blueprints.auth import bp
from models.user import User
from app import db
# Pastikan file forms/auth.py sudah dibuat seperti di atas
from forms.auth import LoginForm 

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect cerdas berdasarkan role jika user refresh halaman login
        if current_user.role == 'admin':
            return redirect(url_for('analytics.dashboard'))
        return redirect(url_for('sales.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # Cek user dan password
        if user is None or not user.check_password(form.password.data):
            flash('Username atau password salah', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        # Handle "Next" argument untuk redirect kembali ke halaman sebelumnya
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            # LOGIC BARU: Arahkan sesuai Role
            if user.role == 'admin':
                next_page = url_for('analytics.dashboard')
            else:
                next_page = url_for('sales.dashboard')
                
        return redirect(next_page)
    
    return render_template('login.html', title='Login', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))