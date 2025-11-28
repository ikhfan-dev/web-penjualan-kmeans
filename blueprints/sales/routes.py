from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from blueprints.sales import bp
from models.customer import Customer
from models.product import Product
from models.transaction import Transaction, TransactionItem
from models.analytics import CustomerSegment, CustomerSegmentMembership, Promotion
from app import db
from datetime import datetime
from decimal import Decimal
from utils.decorators import role_required

@bp.route('/dashboard')
@role_required('admin', 'cashier')
@login_required
def dashboard():
    from models.product import Product
    from models.customer import Customer
    from models.transaction import Transaction
    from datetime import datetime, date
    
    # Get counts for summary cards
    products_count = Product.query.count()
    customers_count = Customer.query.count()
    
    today = date.today()
    today_transactions = Transaction.query.filter(
        db.func.date(Transaction.created_at) == today
    ).count()
    
    low_stock_products = Product.query.filter(Product.stock < 10).all()
    low_stock_count = len(low_stock_products)
    
    # Get recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()
    
    # Get top customers by transaction count
    top_customers = db.session.query(
        Customer.id, Customer.name, db.func.count(Transaction.id).label('transaction_count')
    ).join(Transaction).group_by(Customer.id).order_by(db.desc('transaction_count')).limit(5).all()
    
    return render_template('sales/dashboard.html', 
                          products_count=products_count,
                          customers_count=customers_count,
                          today_transactions=today_transactions,
                          low_stock_count=low_stock_count,
                          recent_transactions=recent_transactions,
                          low_stock_products=low_stock_products,
                          top_customers=top_customers)

@bp.route('/pos')
@role_required('admin', 'cashier')
@login_required
def pos():
    return render_template('sales/pos.html')

@bp.route('/transactions')
@role_required('admin', 'cashier')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    
    query = Transaction.query
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            next_day = filter_date.replace(day=filter_date.day + 1) if filter_date.day < 31 else filter_date
            query = query.filter(
                Transaction.created_at >= filter_date,
                Transaction.created_at < next_day
            )
        except ValueError:
            flash('Format tanggal tidak valid', 'danger')
    
    transactions = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('sales/transactions.html', 
                          transactions=transactions, 
                          date_filter=date_filter)

@bp.route('/transaction/<int:id>')
@role_required('admin', 'cashier')
@login_required
def transaction_detail(id):
    transaction = Transaction.query.get_or_404(id)
    return render_template('sales/transaction_detail.html', transaction=transaction)

@bp.route('/api/checkout', methods=['POST'])
@login_required
def api_checkout():
    data = request.get_json()
    
    if not data or 'items' not in data or 'customer_id' not in data:
        return jsonify({'success': False, 'message': 'Data tidak lengkap'}), 400
    
    customer_id = data['customer_id']
    items = data['items']
    payment_method = data.get('payment_method', 'cash')
    notes = data.get('notes', '')
    promotion_type = data.get('promotion_type')
    promotion_value = data.get('promotion_value')
    discount_amount = data.get('discount_amount', 0.0)
    
    # Validate customer
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'success': False, 'message': 'Pelanggan tidak ditemukan'}), 404
    
    # Create transaction
    transaction = Transaction(
        customer_id=customer_id,
        user_id=current_user.id,
        payment_method=payment_method,
        notes=notes,
        total_amount=0, # Akan dihitung ulang di bawah
        discount_amount=discount_amount # <-- SIMPAN DISKON
    )
    
    # Add items and calculate total
    total_amount = Decimal('0')
    for item in items:
        product = Product.query.get(item['product_id'])
        if not product:
            return jsonify({'success': False, 'message': f'Produk dengan ID {item["product_id"]} tidak ditemukan'}), 404
        
        if product.stock < item['quantity']:
            return jsonify({'success': False, 'message': f'Stok produk {product.name} tidak mencukupi'}), 400
        
        # Update product stock
        product.stock -= item['quantity']
        
        # Add transaction item
        transaction_item = TransactionItem(
            product_id=product.id,
            quantity=item['quantity'],
            price=product.price
        )
        transaction.items.append(transaction_item)
        
        # Calculate subtotal
        subtotal = Decimal(str(product.price)) * Decimal(str(item['quantity']))
        total_amount += subtotal
        
        # Hitung final total di server untuk keamanan
        final_total = total_amount - discount_amount
        transaction.total_amount = final_total
    
    transaction.total_amount = float(total_amount)
    
    # Save transaction
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'transaction_id': transaction.id,
        'total_amount': transaction.total_amount,
        'discount_amount': transaction.discount_amount
    })

@bp.route('/api/customer-segments/<int:customer_id>')
@login_required
def api_customer_segments(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Get customer segments and promotions
    data = db.session.query(CustomerSegmentMembership, CustomerSegment, Promotion)\
        .join(CustomerSegmentMembership.segment)\
        .outerjoin(CustomerSegment.promotion)\
        .filter(CustomerSegmentMembership.customer_id == customer_id)\
        .all()
    
    segment_info = []
    promotions = []
    for membership, segment, promotion in data:
        segment_info.append({
            'id': segment.id,
            'name': segment.segment_name,
            'description': segment.description,
            'color': segment.color,
            'assigned_at': membership.assigned_at.strftime('%Y-%m-%d')
        })
        
        if promotion:
            promotions.append({
                'type': promotion.promotion_type,
                'value': promotion.promotion_value,
                'description': promotion.description
            })
    
    return jsonify({
        'customer': {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email
        },
        'segments': segment_info,
        'promotions': promotions
    })