#C:\Users\Erick Lopez\Desktop\eccomerce\app\models.py
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid
from datetime import datetime, timedelta



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
    tipo_moneda = db.Column(db.String(10), nullable=False)



class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    nombre_usuario = db.Column(db.String(1000), nullable=False)
    password_hash = db.Column(db.String(255))
    es_administrador = db.Column(db.Boolean, default=False)
    es_vendedor = db.Column(db.Boolean, default=False)
    margen_personalizado = db.Column(db.Float, default=0.20)  #20% por defecto
    rfc = db.Column(db.String(100), nullable=True, unique=True)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Producto(db.Model):
    __tablename__ = 'productos'
    id_producto = db.Column(db.Integer, primary_key=True)
    codigo_articulo = db.Column(db.Text, nullable=False)
    nombre_art = db.Column(db.Text, nullable=False)
    marca = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    existencia = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Integer)
    precioOriginal = db.Column(db.Float)
    multiplo_venta = db.Column(db.Integer)
    equivalencia = db.Column(db.Text)
    posicion = db.Column(db.Text)
    esFavorito = db.Column(db.Boolean)
    def calcular_precio_final(self, usuario=None):
        iva = 0.16  # 16% de IVA
        margen_utilidad = 0.10 if usuario and usuario.es_vendedor else 0.20  # 10% para vendedores, 20% de lo contrario
        precio_base = self.precio
        precio_con_iva = precio_base * (1 + iva)
        precio_final = precio_con_iva * (1 + margen_utilidad)
        return round(precio_final, 2)

    def to_dict(self, usuario=None):
        precio_final = self.calcular_precio_final()
        precio_vendedor = self.calcular_precio_final(usuario) if usuario and usuario.es_vendedor else precio_final
        
        return {
            'id_producto': self.id_producto,
            'nombre_art': self.nombre_art,
            'codigo_articulo': self.codigo_articulo,
            'marca': self.marca,
            'precio': self.precio,
            'existencia': self.existencia,
            'equivalencia': self.equivalencia,
            'posicion': self.posicion,
            'multiplo_venta': self.multiplo_venta,
            'rating': self.rating,
            'precio_final': precio_final,
            'precio_vendedor': precio_vendedor  # Agregado para mostrar precio de vendedor
        }

class Cartsession(db.Model):
    __tablename__ = 'cartsession'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=datetime.utcnow() + timedelta(days=7))

class Cartitem(db.Model):
    __tablename__ = 'cartitem'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('productos.id_producto'))
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    cartsession = db.Column(db.String(36), db.ForeignKey('cartsession.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    product = db.relationship('Producto')
    user = db.relationship('Usuario')

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)  # Ahora nullable
    guest_email = db.Column(db.String(100), nullable=True)  # Para usuarios no registrados
    status = db.Column(db.String(50), default='Pendiente')
    total = db.Column(db.Float)
    phone = db.Column(db.String(10))  # Número de teléfono de contacto
    shipping_address = db.relationship('ShippingAddress', backref='order')
    order_items = db.relationship('OrderItem', backref='order', lazy='dynamic')
    cartsession_id = db.Column(db.String(36), nullable=True)  # Asumiendo que usas un UUID como ID de sesión

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('productos.id_producto'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    product = db.relationship('Producto', backref='order_items')

class ShippingAddress(db.Model):
    __tablename__ = 'shipping_address'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(5))
    state = db.Column(db.String(100))

