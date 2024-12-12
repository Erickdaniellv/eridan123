#C:\Users\Erick Lopez\Desktop\eccomerce\app\models.py
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid
from datetime import datetime, timedelta
from sqlalchemy.types import Enum
from sqlalchemy.dialects.postgresql import JSON
import json



class MiTabla(db.Model):
    __tablename__ = 'saldos_cartera'  # Nombre opcional de la tabla

    id = db.Column(db.Integer, primary_key=True)
    empresa = db.Column(db.Integer, nullable=False)
    llave_sucursal_doc = db.Column(db.String(20), nullable=False)
    sucursal = db.Column(db.Integer, nullable=False)
    cartera = db.Column(db.Integer, nullable=False)
    tipo_movimiento = db.Column(db.String(10), nullable=False)
    cod_cliente = db.Column(db.String(10), nullable=False)
    nombre_cliente = db.Column(db.String(255), nullable=False)
    limite_credito = db.Column(db.Numeric, nullable=True)  # Puede ser NULL según el ejemplo
    documento = db.Column(db.String(20), nullable=False)
    fecha_documento = db.Column(db.Date, nullable=False)
    fecha_movimiento = db.Column(db.Date, nullable=False)
    dias_transcurridos = db.Column(db.Integer, nullable=False)
    importe_original = db.Column(db.Numeric, nullable=False)
    importe_iva = db.Column(db.Numeric, nullable=False)
    tasa_iva = db.Column(db.Numeric, nullable=False)
    saldo_actual = db.Column(db.Numeric, nullable=False)
    tipo_moneda = db.Column(Enum('PESOS', 'DOLARES', name='tipo_moneda_enum'), nullable=False)



class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    nombre_usuario = db.Column(db.String(1000), nullable=False)
    password_hash = db.Column(db.String(255))
    es_administrador = db.Column(db.Boolean, default=False)
    es_vendedor = db.Column(db.Boolean, default=False)
    margen_personalizado = db.Column(db.Float, default=0.20)
    rfc = db.Column(db.String(100), nullable=True, unique=True)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)




class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio_base = db.Column(db.Float, nullable=False)



class Tamano(db.Model):
    __tablename__ = 'tamanos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(20), nullable=False, unique=True)
    precio_extra = db.Column(db.Float, nullable=False)

class Opcion(db.Model):
    __tablename__ = 'opciones'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=True)  # Permitir NULL
    nombre = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    precio_extra = db.Column(db.Float, nullable=False)


class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    productos_str = db.Column(db.Text, nullable=True)
    total = db.Column(db.Float, default=0.0)
    estado = db.Column(db.String(20), default='en curso')

    @property
    def productos(self):
        if self.productos_str:
            return json.loads(self.productos_str)
        return []

    @productos.setter
    def productos(self, value):
        self.productos_str = json.dumps(value)
