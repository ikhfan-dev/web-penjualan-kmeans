from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user

def role_required(*roles):
    """
    Decorator untuk memastikan pengguna memiliki salah satu dari role yang diizinkan.
    Contoh penggunaan: @role_required('admin', 'cashier')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Cek apakah user sudah login?
            if not current_user.is_authenticated:
                flash('Silakan login untuk mengakses halaman ini.', 'warning')
                # Arahkan ke login, simpan halaman tujuan di parameter 'next'
                return redirect(url_for('auth.login', next=request.path))
            
            # 2. Cek apakah role user sesuai?
            if current_user.role not in roles:
                flash('Akses Ditolak: Anda tidak memiliki izin untuk halaman ini.', 'danger')
                # Jika dia admin/kasir yang nyasar, kembalikan ke dashboard utama
                return redirect(url_for('sales.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator shortcut khusus untuk role 'admin'.
    """
    return role_required('admin')(f)