from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from blueprints.segments import bp
# Import dari folder forms yang benar
from forms.segments import SegmentForm 
from models.analytics import CustomerSegment, CustomerSegmentMembership
from app import db
from utils.decorators import admin_required

@bp.route('/')
@admin_required
@login_required
def list_segments():
    # Menampilkan list segmen. 
    # Idealnya di template nanti ditampilkan juga jumlah member per segmen.
    segments = CustomerSegment.query.order_by(CustomerSegment.segment_name).all()
    return render_template('segments/list.html', segments=segments)

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
@login_required
def edit_segment(id):
    segment = CustomerSegment.query.get_or_404(id)
    form = SegmentForm(obj=segment)
    
    if form.validate_on_submit():
        # Cek nama segmen ganda (kecuali punya diri sendiri)
        existing_segment = CustomerSegment.query.filter(
            CustomerSegment.segment_name == form.segment_name.data,
            CustomerSegment.id != id
        ).first()
        
        if existing_segment:
            flash(f'Nama segmen "{form.segment_name.data}" sudah digunakan.', 'warning')
            return render_template('segments/form.html', form=form, title='Edit Segmen')
        
        segment.segment_name = form.segment_name.data
        segment.description = form.description.data
        segment.color = form.color.data
        
        db.session.commit()
        flash('Segmen berhasil diperbarui!', 'success')
        # Redirect kembali ke dashboard analytics atau list segmen
        return redirect(url_for('segments.list_segments'))
    
    return render_template('segments/form.html', form=form, title='Edit Segmen')

@bp.route('/delete/<int:id>', methods=['POST'])
@admin_required
@login_required
def delete_segment(id):
    segment = CustomerSegment.query.get_or_404(id)
    
    # Cek apakah segmen ini memiliki member (pelanggan)
    member_count = CustomerSegmentMembership.query.filter_by(segment_id=id).count()
    
    if member_count > 0:
        flash(f'Gagal menghapus: Segmen ini masih memiliki {member_count} pelanggan. Silakan jalankan ulang K-Means untuk mereset segmen.', 'danger')
        return redirect(url_for('segments.list_segments'))

    db.session.delete(segment)
    db.session.commit()
    flash('Segmen berhasil dihapus!', 'success')
    return redirect(url_for('segments.list_segments'))