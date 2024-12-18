from flask_wtf import FlaskForm
from wtforms import  HiddenField, RadioField, SelectMultipleField, FloatField, StringField, DecimalField, PasswordField, BooleanField, SubmitField, TextAreaField, IntegerField, SelectField
from wtforms.validators import NumberRange, DataRequired, Email, EqualTo, Length, Optional, Regexp  # Importa Regexp correctamente
from .constants import POSICIONES, SUCURSALES, JERARQUIA_POSICIONES  # Importa la lista de posiciones
from wtforms.widgets import ListWidget, CheckboxInput




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
    tamano = SelectField(
        'Selecciona el Tamaño',
        choices=[],  # Las opciones se llenarán dinámicamente en la ruta
        validators=[DataRequired(message="El nombre del tamaño es obligatorio.")],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
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
    submit_guardar = SubmitField(
        'Guardar Tamaño',
        render_kw={"class": "bg-green-500 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg shadow"}
    )
    submit_agregar = SubmitField(
        'Agregar al Pedido',
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



class SeleccionarTamanoForm(FlaskForm):
    tamano = RadioField(
        'Selecciona el Tamaño',
        validators=[DataRequired(message="Seleccionar un tamaño es obligatorio.")],
        choices=[],
        render_kw={"class": "mt-1 block w-full p-2 border border-gray-300 rounded-lg"}
    )
    submit = SubmitField(
        'Seleccionar Tamaño',
        render_kw={"class": "bg-blue-500 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg shadow"}
    )

class SeleccionarLecheForm(FlaskForm):
    leche = RadioField('Selecciona el Tipo de Leche', validators=[DataRequired()], choices=[])
    submit = SubmitField('Siguiente')

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class SeleccionarExtrasForm(FlaskForm):
    extras = SelectMultipleField('Selecciona los Extras', validators=[Optional()], coerce=int)
    submit = SubmitField('Añadir al Pedido')

class FinalizarPedidoForm(FlaskForm):
    submit_agregar = SubmitField('Añadir Otro Producto')
    submit_finalizar = SubmitField('Finalizar Pedido')

class SurtirPedidoForm(FlaskForm):
    pedido_id = HiddenField('Pedido ID', validators=[DataRequired()])
    submit = SubmitField('Atender')

class ActualizarEstadoForm(FlaskForm):
    estado = HiddenField('Estado', validators=[DataRequired()])
    submit = SubmitField('Actualizar Estado')


class EmpleadoForm(FlaskForm):
    sucursal = SelectField(
        'Sucursal',
        choices=[(sucursal, sucursal) for sucursal in SUCURSALES],
        validators=[DataRequired(message="La sucursal es requerida.")],
        render_kw={"class": "w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"}
    )
    nombre_puesto = SelectField(
        'Nombre del Puesto',
        choices=[(puesto, puesto) for puesto in POSICIONES],
        validators=[
            DataRequired(message="El nombre del puesto es requerido."),
            Length(max=100, message="El nombre del puesto no puede exceder 100 caracteres.")
        ],
        render_kw={"class": "w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"}
    )
    nombre_persona = StringField(
        'Nombre de la Persona',
        validators=[
            DataRequired(message="El nombre de la persona es requerido."),
            Length(max=100, message="El nombre de la persona no puede exceder 100 caracteres.")
        ],
        render_kw={"class": "w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"}
    )
    supervisor_id = SelectField(
        'Supervisor',
        choices=[],  # Inicialmente vacío, se llenará en la vista
        validators=[Optional()],
        render_kw={"class": "w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"}
    )
    submit = SubmitField(
        'Guardar Empleado',
        render_kw={"class": "w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-md shadow focus:outline-none focus:ring-2 focus:ring-blue-500"}
    )
