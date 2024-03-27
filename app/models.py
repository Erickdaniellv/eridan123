#C:\Users\Erick Lopez\Desktop\eccomerce\app\models.py
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid
from datetime import datetime, timedelta


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


class Facebook(db.Model):
    __tablename__ = 'facebook'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    fotos = db.Column(db.String(255), nullable=False)  # Considera cambiar esto según cómo manejes las fotos
    tipo_de_vehiculo = db.Column(db.String(255), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    marca = db.Column(db.String(255), nullable=False)
    carroceria = db.Column(db.String(255), nullable=False)
    color_exterior = db.Column(db.String(255), nullable=False)
    color_interior = db.Column(db.String(255), nullable=False)
    estado_vehiculo = db.Column(db.String(255), nullable=False)
    tipo_combustible = db.Column(db.String(255), nullable=False)
    transmision = db.Column(db.String(255), nullable=False)
    modelo = db.Column(db.String(255), nullable=False)
    millaje = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)


class SubastaVentura(db.Model):
    __tablename__ = 'subastaventura'
    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String)
    modelo = db.Column(db.String)
    ano = db.Column(db.Integer)
    vin = db.Column(db.String, unique=True)
    precio_siniestro = db.Column(db.String)
    fecha_subasta = db.Column(db.String)
    condicion_venta = db.Column(db.String)
    niu = db.Column(db.String)
    vendedor = db.Column(db.String)
    ubicacion = db.Column(db.String)
    color = db.Column(db.String)
    torre = db.Column(db.String)
    urlsimagenes = db.Column(db.String, nullable=True)  # Ahora puede ser NULL
    urlsdocumentos = db.Column(db.String, nullable=True)  # Ahora puede ser NULL
    urlsimagenes3aws = db.Column(db.String, nullable=True)  # Ahora puede ser NULL
    urlsdocumentos3aws = db.Column(db.String, nullable=True)  # Ahora puede ser NULL 

class Subastasusa(db.Model):
    __tablename__ = 'subastasusa'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)
    titulo = db.Column(db.String)
    vin = db.Column(db.String, unique=True)
    description = db.Column(db.String)  
    subasta = db.Column(db.String)  
    numeroLote = db.Column(db.String)  
    urlSubasta = db.Column(db.String)  
    saleDate = db.Column(db.String)  
    location = db.Column(db.String)  
    state = db.Column(db.String)
    odometer = db.Column(db.String)  
    manufacturer = db.Column(db.String)
    model = db.Column(db.String)
    sku = db.Column(db.String)
    mpn = db.Column(db.String)
    productionDate = db.Column(db.String)
    modelDate = db.Column(db.String)
    vehicleModelDate = db.Column(db.String)
    color = db.Column(db.String)
    vehicleTransmission = db.Column(db.String)
    knownVehicleDamages = db.Column(db.String)
    purchaseDate = db.Column(db.String)
    image = db.Column(db.String)
    brand = db.Column(db.String)
    engineType = db.Column(db.String)
    fuelType = db.Column(db.String)
    offerPrice = db.Column(db.String)
    offerCurrency = db.Column(db.String)
    seller = db.Column(db.String)



class Traslados(db.Model):
    __tablename__ = 'traslados'
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String, nullable=False)
    ubicacion_destino = db.Column(db.String, nullable=False)
    ubicacion_origen = db.Column(db.String, nullable=False)
    state = db.Column(db.String, nullable=False)
    costo_sedan = db.Column(db.Float, nullable=False)
    costo_suv = db.Column(db.Float, nullable=False)  
    dia_levanta = db.Column(db.String, nullable=False) 


class Autos(db.Model):
    __tablename__ = 'autos'
    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    ano = db.Column(db.Integer)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha de registro de la unidad
    vin = db.Column(db.String(100))  # VIN del auto
    numero_lote = db.Column(db.String(100))  # Número de lote
    nombre_subasta = db.Column(db.String(100))  # Copart, Iaai, Otra
    localidad = db.Column(db.String(100))  # Localidad de la subasta
    img = db.Column(db.String(255))  # URL o path de las imágenes del auto en subasta

class Costoauto(db.Model):
    __tablename__ = 'costoauto'
    id = db.Column(db.Integer, primary_key=True)
    auto_id = db.Column(db.Integer, db.ForeignKey('autos.id'), nullable=False)
    costo_adquisicion = db.Column(db.Float, nullable=False)
    costo_reparacion = db.Column(db.Float, nullable=True)
    costo_traslado = db.Column(db.Float, nullable=True)
    costo_otros = db.Column(db.Float, nullable=True)
    costo_importacion = db.Column(db.Float, nullable=True)  # Nuevo campo
    costo_honorarios = db.Column(db.Float, nullable=True)  # Nuevo campo
    costo_flete_obr = db.Column(db.Float, nullable=True)  # Nuevo campo
    costo_partes = db.Column(db.Float, nullable=True)  # Nuevo campo
    costo_carrocero = db.Column(db.Float, nullable=True)  # Nuevo campo
    costo_limpieza = db.Column(db.Float, nullable=True)  # Nuevo campo
    costo_gasolina = db.Column(db.Float, nullable=True)  # Nuevo campo
    costo_carlos = db.Column(db.Float, nullable=True)  # Suponiendo que es otro tipo de costo
    costo_millas = db.Column(db.Float, nullable=True)  # Nuevo campo
    fecha_registro_costo = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con la tabla Autos
    auto = db.relationship('Autos', backref=db.backref('costos', lazy=True))

    def __init__(self, auto_id, costo_adquisicion, costo_reparacion=None, costo_traslado=None, costo_otros=None, costo_importacion=None, costo_honorarios=None, costo_flete_obr=None, costo_partes=None, costo_carrocero=None, costo_limpieza=None, costo_gasolina=None, costo_carlos=None, costo_millas=None):
        self.auto_id = auto_id
        self.costo_adquisicion = costo_adquisicion
        self.costo_reparacion = costo_reparacion
        self.costo_traslado = costo_traslado
        self.costo_otros = costo_otros
        self.costo_importacion = costo_importacion
        self.costo_honorarios = costo_honorarios
        self.costo_flete_obr = costo_flete_obr
        self.costo_partes = costo_partes
        self.costo_carrocero = costo_carrocero
        self.costo_limpieza = costo_limpieza
        self.costo_gasolina = costo_gasolina
        self.costo_carlos = costo_carlos
        self.costo_millas = costo_millas

class Inversiones(db.Model):
    __tablename__ = 'inversiones'
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(255)) 
    monto = db.Column(db.Float)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha_inversion = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha de la inversión
