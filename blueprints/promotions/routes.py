from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from blueprints.promotions import bp
from blueprints.promotions.forms import PromotionForm
from models.analytics import CustomerSegment, Promotion
from app import db
from utils.decorators import admin_required

@bp.route('/')
@admin_required
@login_required
def list_promotions():
    # Join untuk mendapatkan nama segmen
    promotions = db.session.query(Promotion, CustomerSegment)\
        .join(CustomerSegment.promotion)\
        .all()
    
    return render_template('promotions/list.html', promotions=promotions)

@bp.route('/add', methods=['GET', 'POST'])
@admin_required
@login_required
def add_promotion():
    form = PromotionForm()
    
    # Isi pilihan segmen secara dinamis
    segments = CustomerSegment.query.all()
    form.segment_id.choices = [(s.id, s.segment_name) for s in segments]
    
    if form.validate_on_submit():
        # Periksa apakah segmen sudah memiliki promosi
        existing_promotion = Promotion.query.filter_by(segment_id=form.segment_id.data).first()
        if existing_promotion:
            flash(f'Segmen "{segments[form.segment_id.data-1].segment_name}" sudah memiliki promosi.', 'warning')
            return render_template('promotions/form.html', form=form, title='Tambah Promosi')
        
        promotion = Promotion(
            segment_id=form.segment_id.data,
            promotion_type=form.promotion_type.data,
            promotion_value=form.promotion_value.data,
            description=form.description.data
        )
        db.session.add(promotion)
        db.session.commit()
        flash('Promosi berhasil ditambahkan!', 'success')
        return redirect(url_for('promotions.list_promotions'))
    
    return render_template('promotions/form.html', form=form, title='Tambah Promosi')

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
@login_required
def edit_promotion(id):
    promotion = Promotion.query.get_or_404(id)
    form = PromotionForm(obj=promotion)
    
    # Isi pilihan segmen
    segments = CustomerSegment.query.all()
    form.segment_id.choices = [(s.id, s.segment_name) for s in segments]
    
    if form.validate_on_submit():
        # Periksa apakah segmen sudah memiliki promosi (dari promosi lain)
        existing_promotion = Promotion.query.filter(
            Promotion.segment_id == form.segment_id.data,
            Promotion.id != id
        ).first()
        if existing_promotion:
            flash(f'Segmen "{segments[form.segment_id.data-1].segment_name}" sudah memiliki promosi lain.', 'warning')
            return render_template('promotions/form.html', form=form, title='Edit Promosi')
        
        promotion.segment_id = form.segment_id.data
        promotion.promotion_type = form.promotion_type.data
        promotion.promotion_value = form.promotion_value.data
        promotion.description = form.description.data
        
        db.session.commit()
        flash('Promosi berhasil diperbarui!', 'success')
        return redirect(url_for('promotions.list_promotions'))
    
    return render_template('promotions/form.html', form=form, title='Edit Promosi')

@bp.route('/delete/<int:id>', methods=['POST'])
@admin_required
@login_required
def delete_promotion(id):
    promotion = Promotion.query.get_or_404(id)
    segment_name = promotion.segment.segment_name
    db.session.delete(promotion)
    db.session.commit()
    flash(f'Promosi untuk segmen "{segment_name}" berhasil dihapus.', 'success')
    return redirect(url_for('promotions.list_promotions'))

# API untuk mendapatkan detail promosi (opsional, untuk referensi)
@bp.route('/api/<int:id>')
@admin_required
@login_required
def api_promotion_detail(id):
    promotion = Promotion.query.get_or_404(id)
    return jsonify({
        'segment_name': promotion.segment.segment_name,
        'promotion_type': promotion.promotion_type,
        'promotion_value': promotion.promotion_value,
        'description': promotion.description
    })