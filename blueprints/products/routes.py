from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from blueprints.products import bp
from models.product import Product
from app import db
# Pastikan file forms/products.py sudah dibuat
from forms.products import ProductForm
from utils.decorators import admin_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

@bp.route('/')
@login_required # Semua user login boleh lihat list produk
def list_products():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('q', '')

    query = Product.query

    if search_query:
        query = query.filter(
            or_(
                Product.name.ilike(f'%{search_query}%'),
                Product.sku.ilike(f'%{search_query}%'),
                Product.category.ilike(f'%{search_query}%')
            )
        )
    
    # Urutkan berdasarkan nama
    query = query.order_by(Product.name.asc())

    products = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('products/list.html', 
                          products=products, 
                          current_page=page,
                          per_page=per_page,
                          search_query=search_query)

@bp.route('/add', methods=['GET', 'POST'])
@admin_required # Hanya admin yang boleh tambah barang
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        # Cek SKU Unik
        existing_product = Product.query.filter_by(sku=form.sku.data).first()
        if existing_product:
            flash(f'SKU/Barcode {form.sku.data} sudah digunakan oleh produk lain.', 'warning')
            return render_template('products/form.html', form=form, title='Tambah Produk')

        product = Product(
            sku=form.sku.data,
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock=form.stock.data,
            category=form.category.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Produk berhasil ditambahkan!', 'success')
        return redirect(url_for('products.list_products'))
    
    return render_template('products/form.html', form=form, title='Tambah Produk')

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    
    if form.validate_on_submit():
        # Cek SKU Unik (kecuali punya diri sendiri)
        existing_sku = Product.query.filter(Product.sku == form.sku.data, Product.id != id).first()
        if existing_sku:
            flash(f'SKU/Barcode {form.sku.data} sudah digunakan oleh produk lain.', 'warning')
            return render_template('products/form.html', form=form, title='Edit Produk')

        product.sku = form.sku.data
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.stock = form.stock.data
        product.category = form.category.data
        
        db.session.commit()
        flash('Produk berhasil diperbarui!', 'success')
        return redirect(url_for('products.list_products'))
    
    return render_template('products/form.html', form=form, title='Edit Produk')

@bp.route('/delete/<int:id>', methods=['POST'])
@admin_required
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Produk berhasil dihapus!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Gagal menghapus: Produk ini sudah pernah terjual (ada di riwayat transaksi). Silakan set stok ke 0 atau non-aktifkan saja.', 'danger')
    
    return redirect(url_for('products.list_products'))

@bp.route('/api/search')
@login_required
def api_search():
    # API ini digunakan oleh halaman Kasir (Sales)
    query = request.args.get('q', '')
    
    # Jika query kosong, jangan return apa-apa
    if not query:
        return jsonify([])

    # Prioritaskan pencarian SKU (exact match) untuk barcode scanner
    exact_sku = Product.query.filter_by(sku=query).first()
    if exact_sku:
         return jsonify([{
            'id': exact_sku.id,
            'name': exact_sku.name,
            'sku': exact_sku.sku,
            'price': float(exact_sku.price), # Decimal to Float for JSON
            'stock': exact_sku.stock
        }])

    # Jika tidak exact match, cari loose match (nama atau sku mirip)
    products = Product.query.filter(
        or_(
            Product.name.ilike(f'%{query}%'),
            Product.sku.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'price': float(product.price),
            'stock': product.stock
        })
    
    return jsonify(results)