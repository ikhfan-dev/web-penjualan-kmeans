from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from blueprints.users import bp
from models.user import User
from forms.users import ProfileForm, UserForm
from app import db
from utils.decorators import admin_required
from werkzeug.security import generate_password_hash

# --- 1. PROFIL SAYA (Admin Edit, Kasir View) ---
@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    
    # Jika bukan admin, form hanya untuk display (disable validasi post)
    if current_user.role != 'admin':
        # Tidak memproses POST untuk non-admin demi keamanan
        pass
    elif form.validate_on_submit():
        # Cek Username unik (jika berubah)
        existing_user = User.query.filter(User.username == form.username.data, User.id != current_user.id).first()
        if existing_user:
            flash('Username sudah digunakan.', 'warning')
            return render_template('users/profile.html', form=form)

        # Cek Email unik
        existing_email = User.query.filter(User.email == form.email.data, User.id != current_user.id).first()
        if existing_email:
            flash('Email sudah digunakan.', 'warning')
            return render_template('users/profile.html', form=form)

        current_user.username = form.username.data
        current_user.email = form.email.data
        
        # Ganti Password jika diisi
        if form.password.data:
            current_user.set_password(form.password.data)
            
        db.session.commit()
        flash('Profil berhasil diperbarui.', 'success')
        return redirect(url_for('users.profile'))
        
    return render_template('users/profile.html', form=form)

# --- 2. MANAJEMEN PENGGUNA (Admin Only) ---

@bp.route('/manage')
@admin_required
@login_required
def list_users():
    users = User.query.order_by(User.role.asc(), User.username.asc()).all()
    return render_template('users/list.html', users=users)

@bp.route('/manage/add', methods=['GET', 'POST'])
@admin_required
@login_required
def add_user():
    form = UserForm()
    # Password Wajib saat Add New
    form.password.flags.required = True
    
    if form.validate_on_submit():
        if not form.password.data:
            flash('Password wajib diisi untuk pengguna baru.', 'danger')
            return render_template('users/form.html', form=form, title='Tambah Pengguna')
            
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('Username atau Email sudah terdaftar.', 'warning')
            return render_template('users/form.html', form=form, title='Tambah Pengguna')
        
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        new_user.set_password(form.password.data)
        
        db.session.add(new_user)
        db.session.commit()
        flash(f'Pengguna {new_user.username} berhasil ditambahkan.', 'success')
        return redirect(url_for('users.list_users'))
        
    return render_template('users/form.html', form=form, title='Tambah Pengguna')

@bp.route('/manage/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
@login_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        # Cek Duplikat
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data), 
            User.id != id
        ).first()
        
        if existing_user:
            flash('Username atau Email sudah digunakan orang lain.', 'warning')
            return render_template('users/form.html', form=form, title='Edit Pengguna')

        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        
        # Reset Password jika diisi
        if form.password.data:
            user.set_password(form.password.data)
            flash('Password berhasil direset.', 'info')
            
        db.session.commit()
        flash('Data pengguna diperbarui.', 'success')
        return redirect(url_for('users.list_users'))
        
    return render_template('users/form.html', form=form, title='Edit Pengguna')

@bp.route('/manage/delete/<int:id>', methods=['POST'])
@admin_required
@login_required
def delete_user(id):
    if id == current_user.id:
        flash('Anda tidak dapat menghapus akun sendiri.', 'danger')
        return redirect(url_for('users.list_users'))
        
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('Pengguna berhasil dihapus.', 'success')
    return redirect(url_for('users.list_users'))