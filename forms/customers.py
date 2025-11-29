from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length

class CustomerForm(FlaskForm):
    name = StringField('Nama', validators=[
        DataRequired(),
        Length(max=100)
    ])
    phone = StringField('Telepon', validators=[
        DataRequired(),
        Length(min=9, max=15, message="Nomor telepon tidak valid")
    ])
    # Gunakan Optional() agar field boleh kosong.
    # Jika diisi, baru divalidasi format emailnya.
    email = StringField('Email', validators=[Optional(), Email()])
    
    address = TextAreaField('Alamat', validators=[Optional()])
    submit = SubmitField('Simpan')