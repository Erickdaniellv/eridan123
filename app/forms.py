from flask_wtf import FlaskForm
from wtforms import FloatField, StringField, DecimalField, PasswordField, BooleanField, SubmitField, TextAreaField, IntegerField, SelectField
from wtforms.validators import NumberRange, DataRequired, Email, EqualTo, Length, Optional, Regexp  # Importa Regexp correctamente


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
    rfc = StringField('RFC', validators=[Optional()])
    telefono = StringField('Teléfono', validators=[Optional()])
    direccion = StringField('Dirección', validators=[Optional()])
    submit = SubmitField('Registro')

class AdminUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    es_administrador = BooleanField('¿Es Administrador?')
    es_vendedor = BooleanField('¿Es Vendedor?')
    margen_personalizado = FloatField(
        'Margen Personalizado',
        validators=[Optional()]
    )
    submit = SubmitField('Guardar')


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

class ProductForm(FlaskForm):
    nombre = SelectField(
        'Nombre',
        choices=[
            ('Americano', 'Americano'),
            ('Mexicano', 'Mexicano'),
            ('Expresso', 'Expresso'),
            ('Late', 'Late'),
            ('Capuchino', 'Capuchino'),
            ('Mocca', 'Mocca'),
        ],
        validators=[DataRequired()],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    descripcion = TextAreaField(
        'Descripción',
        validators=[Length(max=500)],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    precio_base = DecimalField(
        'Precio Base',
        validators=[DataRequired(), NumberRange(min=0)],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    submit = SubmitField(
        'Guardar',
        render_kw={"class": "bg-green-500 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg shadow"}
    )


class TamanoForm(FlaskForm):
    nombre = SelectField(
        'Nombre del Tamaño',
        choices=[('Mini', 'Mini'), ('Chico', 'Chico'), ('Mediano', 'Mediano'), ('Grande', 'Grande')],
        validators=[DataRequired(message="El nombre del tamaño es obligatorio.")],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    precio_extra = DecimalField(
        'Precio Extra',
        validators=[DataRequired(message="El precio extra es obligatorio."), NumberRange(min=0)],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    submit = SubmitField(
        'Guardar Tamaño',
        render_kw={"class": "bg-green-500 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg shadow"}
    )



class OpcionForm(FlaskForm):
    tipo = SelectField(
        'Tipo',
        choices=[('Edulzante', 'Edulzante'), ('Leche', 'Leche'), ('Extra', 'Extra')],
        validators=[DataRequired()],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    nombre = SelectField(
        'Nombre',
        choices=[],  # Las opciones se rellenarán dinámicamente en la ruta
        validators=[DataRequired()],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    precio_extra = FloatField(
        'Precio Extra',
        validators=[DataRequired(), NumberRange(min=0)],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    submit = SubmitField(
        'Guardar',
        render_kw={"class": "bg-green-500 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg shadow"}
    )
