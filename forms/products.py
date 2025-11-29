from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length

class ProductForm(FlaskForm):
    sku = StringField('SKU / Barcode', validators=[
        DataRequired(),
        Length(max=50)
    ])
    name = StringField('Nama Produk', validators=[
        DataRequired(),
        Length(max=100)
    ])
    description = TextAreaField('Deskripsi')
    
    # DecimalField jauh lebih akurat untuk uang daripada FloatField
    price = DecimalField('Harga (Rp)', validators=[
        DataRequired(), 
        NumberRange(min=0)
    ])
    
    stock = IntegerField('Stok', validators=[
        DataRequired(), 
        NumberRange(min=0)
    ])
    
    category = SelectField('Kategori', choices=[
        ('makanan', 'Makanan'),
        ('minuman', 'Minuman'),
        ('elektronik', 'Elektronik'),
        ('pakaian', 'Pakaian'),
        ('sembako', 'Sembako'),
        ('lainnya', 'Lainnya')
    ], default='lainnya')
    
    unit = StringField('Satuan', validators=[DataRequired()], default='PCS')
    
    submit = SubmitField('Simpan')
    
    # Validasi SKU unik telah dipindahkan ke routes.py (add_product & edit_product)
    # untuk menangani logika Edit ID dengan lebih aman.