from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from blueprints.segments import bp
from blueprints.segments.forms import SegmentForm
from models.analytics import CustomerSegment
from app import db
from utils.decorators import admin_required

@bp.route('/')
@admin_required
@login_required
def list_segments():
    segments = CustomerSegment.query.all()
    return render_template('segments/list.html', segments=segments)

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
@login_required
def edit_segment(id):
    segment = CustomerSegment.query.get_or_404(id)
    form = SegmentForm(obj=segment)
    
    if form.validate_on_submit():
        # Periksa apakah nama segmen sudah ada (kecuali untuk segmen itu sendiri)
        existing_segment = CustomerSegment.query.filter(
            CustomerSegment.segment_name == form.segment_name.data,
            CustomerSegment.id != id
        ).first()
        if existing_segment:
            flash('Nama segmen sudah ada. Silakan gunakan nama lain.', 'warning')
            return render_template('segments/form.html', form=form, title='Edit Segmen')
        
        segment.segment_name = form.segment_name.data
        segment.description = form.description.data
        segment.color = form.color.data
        
        db.session.commit()
        flash('Segmen berhasil diperbarui!', 'success')
        return redirect(url_for('segments.list_segments'))
    
    return render_template('segments/form.html', form=form, title='Edit Segmen')