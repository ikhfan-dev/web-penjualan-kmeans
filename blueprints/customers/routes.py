from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from blueprints.customers import bp
from models.customer import Customer
from models.transaction import Transaction
from app import db
# Pastikan path import ini sesuai struktur folder Anda
from forms.customers import CustomerForm
from utils.decorators import role_required, admin_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

@bp.route('/')
@role_required('admin', 'cashier')
@login_required
def list_customers():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('q', '')

    query = Customer.query

    if search_query:
        # Gunakan ilike untuk PostgreSQL/MySQL agar case-insensitive
        filter_condition = (Customer.name.ilike(f'%{search_query}%')) | \
                           (Customer.phone.ilike(f'%{search_query}%'))
        query = query.filter(filter_condition)
    
    # Urutkan dari yang terbaru atau berdasarkan nama
    query = query.order_by(Customer.name.asc())
    
    customers = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('customers/list.html', 
                          customers=customers, 
                          current_page=page,
                          per_page=per_page,
                          search_query=search_query)

@bp.route('/add', methods=['GET', 'POST'])
@role_required('admin', 'cashier')
@login_required
def add_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        # Validasi Duplikat Manual
        existing_phone = Customer.query.filter_by(phone=form.phone.data).first()
        if existing_phone:
            flash('Nomor telepon sudah terdaftar pada pelanggan lain.', 'warning')
            return render_template('customers/form.html', form=form, title='Tambah Pelanggan')
        
        if form.email.data:
            existing_email = Customer.query.filter_by(email=form.email.data).first()
            if existing_email:
                flash('Email sudah terdaftar.', 'warning')
                return render_template('customers/form.html', form=form, title='Tambah Pelanggan')

        customer = Customer(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data
        )
        db.session.add(customer)
        db.session.commit()
        flash('Pelanggan berhasil ditambahkan!', 'success')
        return redirect(url_for('customers.list_customers'))
    
    return render_template('customers/form.html', form=form, title='Tambah Pelanggan')

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@role_required('admin', 'cashier')
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    
    if form.validate_on_submit():
        # Cek duplikat tapi kecualikan diri sendiri
        existing_phone = Customer.query.filter(Customer.phone == form.phone.data, Customer.id != id).first()
        if existing_phone:
            flash('Nomor telepon sudah digunakan pelanggan lain.', 'warning')
            return render_template('customers/form.html', form=form, title='Edit Pelanggan')

        customer.name = form.name.data
        customer.phone = form.phone.data
        customer.email = form.email.data
        customer.address = form.address.data
        
        db.session.commit()
        flash('Pelanggan berhasil diperbarui!', 'success')
        return redirect(url_for('customers.list_customers'))
    
    return render_template('customers/form.html', form=form, title='Edit Pelanggan')

@bp.route('/delete/<int:id>', methods=['POST'])
@admin_required # Hanya admin yang boleh menghapus data master
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Pelanggan berhasil dihapus!', 'success')
    except IntegrityError:
        # Menangkap error jika pelanggan sudah punya transaksi (Foreign Key Constraint)
        db.session.rollback()
        flash('Gagal menghapus: Pelanggan ini memiliki riwayat transaksi. Data tidak boleh dihapus demi integritas laporan keuangan.', 'danger')
    
    return redirect(url_for('customers.list_customers'))

@bp.route('/api/search')
@login_required
def api_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    # Gunakan ilike agar konsisten dengan search halaman utama
    customers = Customer.query.filter(
        or_(
            Customer.name.ilike(f'%{query}%'),
            Customer.phone.ilike(f'%{query}%'),
            Customer.email.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email or '-'
        })
    
    return jsonify(results)

@bp.route('/transactions/<int:customer_id>')
@role_required('admin', 'cashier')
@login_required
def customer_transactions(customer_id):
    if customer_id == 0:
        flash('Tidak ada riwayat transaksi untuk pelanggan umum.', 'info')
        return redirect(url_for('customers.list_customers'))

    customer = Customer.query.get_or_404(customer_id)
    
    # Tambahkan pagination untuk transaksi (penting jika pelanggan loyal)
    page = request.args.get('page', 1, type=int)
    
    transactions = Transaction.query.filter_by(customer_id=customer_id)\
                                .order_by(Transaction.created_at.desc())\
                                .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('customers/transactions.html', 
                          customer=customer, 
                          transactions=transactions)