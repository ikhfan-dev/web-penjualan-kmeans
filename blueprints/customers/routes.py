from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from blueprints.customers import bp
from models.customer import Customer
from models.transaction import Transaction
from app import db
from forms.customers import CustomerForm
from utils.decorators import role_required, admin_required

@bp.route('/')
@role_required('admin', 'cashier')
@login_required
def list_customers():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    customers = Customer.query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('customers/list.html', 
                          customers=customers, current_page=page,
                          per_page=per_page)

@bp.route('/add', methods=['GET', 'POST'])
@role_required('admin', 'cashier')
@login_required
def add_customer():
    form = CustomerForm()
    if form.validate_on_submit():
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
        customer.name = form.name.data
        customer.phone = form.phone.data
        customer.email = form.email.data
        customer.address = form.address.data
        
        db.session.commit()
        flash('Pelanggan berhasil diperbarui!', 'success')
        return redirect(url_for('customers.list_customers'))
    
    return render_template('customers/form.html', form=form, title='Edit Pelanggan')

@bp.route('/delete/<int:id>', methods=['POST'])
@admin_required
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('Pelanggan berhasil dihapus!', 'success')
    return redirect(url_for('customers.list_customers'))

@bp.route('/api/search')
@login_required
def api_search():
    query = request.args.get('q', '')
    customers = Customer.query.filter(
        (Customer.name.contains(query)) | (Customer.phone.contains(query)) | (Customer.email.contains(query))
    ).limit(10).all()
    
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email
        })
    
    return jsonify(results)

@bp.route('/transactions/<int:customer_id>')
@role_required('admin', 'cashier') # Hanya admin dan kasir yang bisa akses
@login_required
def customer_transactions(customer_id):
    # Jika customer_id adalah 0, ini adalah pelanggan umum
    if customer_id == 0:
        flash('Tidak ada riwayat transaksi untuk pelanggan umum.', 'info')
        return redirect(url_for('customers.list_customers'))

    customer = Customer.query.get_or_404(customer_id)
    
    # Ambil semua transaksi untuk pelanggan ini, urutkan dari yang terbaru
    transactions = Transaction.query.filter_by(customer_id=customer_id)\
                                .order_by(Transaction.created_at.desc())\
                                .all()
    
    return render_template('customers/transactions.html', customer=customer, transactions=transactions)