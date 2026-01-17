from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password Baru', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Konfirmasi Password', validators=[
        Optional(), 
        EqualTo('password', message='Password harus sama')
    ])
    submit = SubmitField('Simpan Perubahan')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[('cashier', 'Kasir'), ('admin', 'Admin')], default='cashier')
    password = PasswordField('Password', validators=[Optional(), Length(min=6)]) # Optional saat edit
    submit = SubmitField('Simpan')