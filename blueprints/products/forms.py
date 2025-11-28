from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from blueprints.products import bp
from models.product import Product
from app import db
from forms.products import ProductForm

@bp.route('/')
@login_required
def list_products():
    products = Product.query.all()
    return render_template('products/list.html', products=products)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
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
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    
    if form.validate_on_submit():
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
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Produk berhasil dihapus!', 'success')
    return redirect(url_for('products.list_products'))

@bp.route('/api/search')
@login_required
def api_search():
    query = request.args.get('q', '')
    products = Product.query.filter(
        (Product.name.contains(query)) | (Product.sku.contains(query))
    ).limit(10).all()
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'price': product.price,
            'stock': product.stock
        })
    
    return jsonify(results)