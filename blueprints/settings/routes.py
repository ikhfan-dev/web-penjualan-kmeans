from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from blueprints.settings import bp
from models.settings import AppSetting
from forms.settings import AppSettingForm
from app import db
from utils.decorators import admin_required

@bp.route('/', methods=['GET', 'POST'])
@admin_required
@login_required
def index():
    # Ambil setting yang ada atau buat default jika belum ada
    setting = AppSetting.query.first()
    if not setting:
        setting = AppSetting(app_name="Aplikasi Penjualan", primary_color="#0d6efd")
        db.session.add(setting)
        db.session.commit()
    
    form = AppSettingForm(obj=setting)
    
    if form.validate_on_submit():
        setting.app_name = form.app_name.data
        setting.primary_color = form.primary_color.data
        
        try:
            db.session.commit()
            flash('Pengaturan aplikasi berhasil diperbarui!', 'success')
            return redirect(url_for('settings.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {e}', 'danger')
            
    return render_template('settings/index.html', form=form, setting=setting)