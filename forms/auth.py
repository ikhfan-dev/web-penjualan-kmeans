from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Ingat Saya')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=4, max=64, message="Username minimal 4 karakter")
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email(message="Format email tidak valid")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message="Password minimal 6 karakter")
    ])
    confirm_password = PasswordField('Ulangi Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Password harus sama')
    ])
    
    # Role sesuai dengan decorator @role_required di routes
    role = SelectField('Role', choices=[
        ('cashier', 'Kasir'),
        ('admin', 'Admin')
    ], default='cashier')
    
    submit = SubmitField('Daftar')
    
    # Catatan: Validasi username/email duplikat sudah ditangani di routes.py 
    # agar pesan error bisa lebih fleksibel (Flash Message).