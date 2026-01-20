from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

import random
from datetime import datetime, timedelta
from faker import Faker

# Inisialisasi Extension di luar fungsi create_app agar bisa diimport
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Init Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
    
    # --- 1. SETUP FILTER TEMPLATE (FORMAT RUPIAH) ---
    @app.template_filter('rp')
    def format_rupiah(value):
        try:
            if value is None:
                return "Rp 0"
            # Format: Rp 10.000 (menggunakan library bawaan python string formatting)
            return f"Rp {float(value):,.0f}".replace(',', '.')
        except (ValueError, TypeError):
            return "Rp 0"

    # --- 1.5 CONTEXT PROCESSOR (APP SETTINGS) ---
    @app.context_processor
    def inject_app_settings():
        try:
            # Import di dalam fungsi untuk menghindari circular import jika ada
            from models.settings import AppSetting
            setting = AppSetting.query.first()
            if not setting:
                # Fallback object jika belum ada di DB (atau tabel belum dibuat)
                setting = {'app_name': 'Aplikasi Penjualan', 'primary_color': '#0d6efd'}
            return dict(app_setting=setting)
        except Exception:
             # Fallback jika terjadi error DB (misal saat migrasi awal)
            return dict(app_setting={'app_name': 'Aplikasi Penjualan', 'primary_color': '#0d6efd'})


    # --- 2. IMPORT MODELS ---
    # Import di sini untuk menghindari circular import
    from models.user import User
    from models.customer import Customer
    from models.product import Product
    from models.transaction import Transaction, TransactionItem
    from models.analytics import CustomerSegment, CustomerSegmentMembership, Promotion
    from models.settings import AppSetting
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # --- 3. REGISTER BLUEPRINTS ---
    from blueprints.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from blueprints.products import bp as products_bp
    app.register_blueprint(products_bp, url_prefix='/products')
    
    from blueprints.customers import bp as customers_bp
    app.register_blueprint(customers_bp, url_prefix='/customers')
    
    from blueprints.sales import bp as sales_bp
    app.register_blueprint(sales_bp, url_prefix='/sales')
    
    from blueprints.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    
    from blueprints.promotions import bp as promotions_bp
    app.register_blueprint(promotions_bp, url_prefix='/promotions')

    from blueprints.segments import bp as segments_bp
    app.register_blueprint(segments_bp, url_prefix='/segments')

    from blueprints.settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')

    from blueprints.users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix='/users')
    
    # --- 4. MAIN ROUTES ---
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    # --- 5. CLI COMMAND: SEED DB ---
    @app.cli.command("seed-db")
    def seed_db_command():
        """Isi database dengan data dummy, jalankan K-Means, dan buat promosi."""
        from utils.seeder import run_seeding
        # `db` sudah diinisialisasi di scope luar create_app, jadi bisa di-pass
        run_seeding(db)


    return app

# Instance aplikasi global untuk Gunicorn
app = create_app()

if __name__ == '__main__':
    # Debug mode dikontrol oleh environment variable FLASK_DEBUG
    is_debug_mode = app.config.get('DEBUG', False)
    app.run(debug=is_debug_mode)