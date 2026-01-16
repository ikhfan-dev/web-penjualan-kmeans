from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from blueprints.sales import bp
from models.customer import Customer
from models.product import Product
from models.transaction import Transaction, TransactionItem
from models.analytics import CustomerSegment, CustomerSegmentMembership, Promotion
from app import db
from datetime import datetime, date, timedelta
from decimal import Decimal
import calendar # <-- Import calendar
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
from utils.decorators import role_required

@bp.route('/dashboard')
@role_required('admin', 'cashier')
@login_required
def dashboard():
    # --- Data untuk Kartu Ringkasan ---
    products_count = Product.query.count()
    customers_count = Customer.query.count()
    today = date.today()
    today_transactions_count = Transaction.query.filter(func.date(Transaction.created_at) == today).count()
    
    # --- Poin 6.1: Omset Bulanan ---
    _, num_days_in_month = calendar.monthrange(today.year, today.month)
    first_day_of_month = date(today.year, today.month, 1)
    last_day_of_month = date(today.year, today.month, num_days_in_month)
    
    monthly_turnover = db.session.query(func.sum(Transaction.total_amount))\
        .filter(Transaction.created_at.between(first_day_of_month, f"{last_day_of_month} 23:59:59"))\
        .scalar() or Decimal('0')

    # --- Data untuk tabel & list di bawah ---
    low_stock_query = Product.query.filter(Product.stock < 10)
    low_stock_count = low_stock_query.count()
    low_stock_products = low_stock_query.limit(5).all()
    
    recent_transactions = Transaction.query.options(joinedload(Transaction.customer), joinedload(Transaction.user))\
        .order_by(Transaction.created_at.desc()).limit(5).all()
    
    top_customers = db.session.query(Customer.id, Customer.name, func.count(Transaction.id).label('transaction_count'))\
        .join(Transaction).group_by(Customer.id).order_by(desc('transaction_count')).limit(5).all()

    # --- Poin 6.2: Perbandingan Transaksi Harian (7 Hari Terakhir) ---
    seven_days_ago = today - timedelta(days=6)
    txs_last_7_days = db.session.query(Transaction.created_at)\
        .filter(Transaction.created_at >= seven_days_ago).all()
    
    day_labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)] # e.g. ['Mon', 'Tue', ...]
    daily_counts = [0] * 7 # [Count for 6 days ago, ..., today]
    
    for tx_time, in txs_last_7_days:
        # Hitung selisih hari dari 'tujuh_hari_lalu'
        day_diff = (tx_time.date() - seven_days_ago).days
        if 0 <= day_diff < 7:
            daily_counts[day_diff] += 1
            
    return render_template('sales/dashboard.html', 
                          products_count=products_count,
                          customers_count=customers_count,
                          today_transactions=today_transactions_count,
                          low_stock_count=low_stock_count,
                          recent_transactions=recent_transactions,
                          low_stock_products=low_stock_products,
                          top_customers=top_customers,
                          monthly_turnover=monthly_turnover, # Data baru
                          day_labels=day_labels,           # Data baru
                          daily_counts=daily_counts)       # Data baru

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
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    # Eager load relasi agar tabel tidak berat
    query = Transaction.query.options(joinedload(Transaction.customer), joinedload(Transaction.user))
    
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(Transaction.created_at >= start_date)
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            # Tambah 1 hari untuk membuat rentang inklusif
            end_date_plus_one = end_date + timedelta(days=1)
            query = query.filter(Transaction.created_at < end_date_plus_one)

    except ValueError:
        flash('Format tanggal tidak valid. Gunakan YYYY-MM-DD.', 'danger')
        start_date_str = ''
        end_date_str = ''

    transactions = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('sales/transactions.html', 
                          transactions=transactions, 
                          start_date=start_date_str,
                          end_date=end_date_str)

@bp.route('/transaction/<int:id>')
@role_required('admin', 'cashier')
@login_required
def transaction_detail(id):
    # Eager load items dan product untuk detail struk
    transaction = Transaction.query.options(
        joinedload(Transaction.items).joinedload(TransactionItem.product),
        joinedload(Transaction.customer)
    ).get_or_404(id)
    
    return render_template('sales/transaction_detail.html', transaction=transaction)

@bp.route('/api/checkout', methods=['POST'])
@login_required
def api_checkout():
    data = request.get_json()
    
    if not data or 'items' not in data or 'customer_id' not in data:
        return jsonify({'success': False, 'message': 'Data tidak lengkap'}), 400
    
    customer_id = data['customer_id']
    items = data['items'] # List of {product_id, quantity}
    payment_method = data.get('payment_method', 'cash')
    notes = data.get('notes', '')
    
    # Validate customer
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'success': False, 'message': 'Pelanggan tidak ditemukan'}), 404
    
    try:
        # Mulai Transaksi Database
        transaction = Transaction(
            customer_id=customer_id,
            user_id=current_user.id,
            payment_method=payment_method,
            notes=notes,
            created_at=datetime.now(),
            # --- PERBAIKAN DI SINI ---
            total_amount=0,      # Isi 0 dulu agar lolos validasi NOT NULL saat autoflush
            discount_amount=0    # Isi 0 dulu
            # -------------------------
        )
        db.session.add(transaction)
        
        total_amount = Decimal('0')
        
        # Proses Item
        for item in items:
            product = Product.query.with_for_update().get(item['product_id']) # Lock Row (PostgreSQL/MySQL InnoDB)
            
            if not product:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Produk ID {item["product_id"]} tidak ditemukan'}), 404
            
            qty = int(item['quantity'])
            if product.stock < qty:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Stok {product.name} kurang. Sisa: {product.stock}'}), 400
            
            # Kurangi Stok
            product.stock -= qty
            
            # Hitung Subtotal
            price = Decimal(str(product.price))
            subtotal = price * qty
            total_amount += subtotal
            
            # Tambah Item ke Transaksi
            transaction_item = TransactionItem(
                transaction=transaction, # Link ke parent
                product_id=product.id,
                quantity=qty,
                price=product.price # Simpan harga saat transaksi terjadi
            )
            db.session.add(transaction_item)
        
        # --- PERBAIKAN LOGIKA DISKON (SERVER SIDE CALCULATION) ---
        # Jangan percaya data diskon dari frontend. Hitung ulang hak promosi user.
        
        discount_amount = Decimal('0')
        
        # Ambil promo aktif untuk customer ini
        active_promotions = db.session.query(Promotion)\
            .join(CustomerSegment, Promotion.segment_id == CustomerSegment.id)\
            .join(CustomerSegmentMembership, CustomerSegment.id == CustomerSegmentMembership.segment_id)\
            .filter(CustomerSegmentMembership.customer_id == customer_id)\
            .all()
            
        # Ambil diskon terbesar yang berhak didapatkan
        for promo in active_promotions:
            current_discount = Decimal('0')
            if promo.promotion_type == 'percentage_discount':
                # Diskon Persen
                val = Decimal(str(promo.promotion_value))
                current_discount = total_amount * (val / 100)
            elif promo.promotion_type == 'fixed_discount':
                # Diskon Rupiah
                val = Decimal(str(promo.promotion_value))
                current_discount = val
            
            # Kita ambil diskon yang paling menguntungkan pelanggan (jika ada tumpang tindih)
            if current_discount > discount_amount:
                discount_amount = current_discount
        
        # Pastikan diskon tidak minus atau melebihi total
        if discount_amount > total_amount:
            discount_amount = total_amount
            
        transaction.total_amount = total_amount - discount_amount
        transaction.discount_amount = discount_amount
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'transaction_id': transaction.id,
            'total_gross': float(total_amount),
            'discount_applied': float(discount_amount),
            'total_net': float(transaction.total_amount)
        })

    except Exception as e:
        db.session.rollback()
        print(f"Checkout Error: {e}") # Log error ke terminal
        return jsonify({'success': False, 'message': 'Terjadi kesalahan sistem saat checkout'}), 500

@bp.route('/api/customer-segments/<int:customer_id>')
@login_required
def api_customer_segments(customer_id):
    # Route ini digunakan frontend POS untuk menampilkan info promo sebelum checkout
    customer = Customer.query.get_or_404(customer_id)
    
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
            'color': segment.color
        })
        
        if promotion:
            promotions.append({
                'type': promotion.promotion_type,
                'value': float(promotion.promotion_value),
                'description': promotion.description
            })
    
    return jsonify({
        'customer': {
            'id': customer.id,
            'name': customer.name,
        },
        'segments': segment_info,
        'promotions': promotions
    })