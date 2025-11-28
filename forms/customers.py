from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email
from models.customer import Customer

class CustomerForm(FlaskForm):
    name = StringField('Nama', validators=[DataRequired()])
    phone = StringField('Telepon')
    email = StringField('Email', validators=[Email()])
    address = TextAreaField('Alamat')
    submit = SubmitField('Simpan')