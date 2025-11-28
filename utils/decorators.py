from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """
    Decorator untuk memastikan pengguna memiliki salah satu dari role yang diizinkan.
    Contoh penggunaan: @role_required('admin', 'cashier')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
                return redirect(url_for('sales.dashboard')) # Aman untuk di-redirect ke dashboard
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator khusus untuk role 'admin'.
    """
    return role_required('admin')(f)