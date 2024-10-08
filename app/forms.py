from flask_wtf import FlaskForm
from wtforms import FloatField, StringField, DecimalField, PasswordField, BooleanField, SubmitField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp  # Importa Regexp correctamente




class RegistrationForm(FlaskForm):
    email = StringField(
        'Email', 
        validators=[
            DataRequired(message="El email es requerido."),
            Email(message="El email no es válido.")
        ]
    )
    username = StringField(
        'Usuario', 
        validators=[
            DataRequired(message="El nombre de usuario es requerido."),
            Length(min=4, max=25, message="El nombre de usuario debe tener entre 4 y 25 caracteres.")
        ]
    )
    password = PasswordField(
        'Contraseña', 
        validators=[
            DataRequired(message="La contraseña es requerida."),
            Length(min=6, max=40, message="La contraseña debe tener entre 6 y 40 caracteres.")
        ]
    )
    confirm_password = PasswordField(
        'Confirma Contraseña', 
        validators=[
            DataRequired(message="La confirmación de la contraseña es requerida."),
            EqualTo('password', message="Las contraseñas deben coincidir.")
        ]
    )
    submit = SubmitField('Registro')

class UserProfileForm(FlaskForm):
    rfc = StringField('RFC', validators=[Optional()])
    telefono = StringField('Teléfono', validators=[Optional()])
    direccion = StringField('Dirección', validators=[Optional()])
    submit = SubmitField('Actualizar Perfil')


class LoginForm(FlaskForm):
    username_or_email = StringField(
        'Usuario o Email', 
        validators=[
            DataRequired(message="El nombre de usuario o email es requerido.")
        ]
    )
    password = PasswordField(
        'Contraseña', 
        validators=[
            DataRequired(message="La contraseña es requerida.")
        ]
    )
    remember = BooleanField('Remember Me')
    submit = SubmitField('Acceso')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Contraseña Actual', validators=[DataRequired()])
    new_password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=6, max=40)])
    confirm_new_password = PasswordField('Confirmar Nueva Contraseña', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Cambiar Contraseña')

class PasswordRecoveryForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Recuperar Contraseña')

