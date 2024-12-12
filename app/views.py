# C:\Users\Erick Lopez2\Desktop\eccomerce\app\app.py
from .models import Pedido, Opcion, Producto, Usuario, MiTabla, Tamano
from flask import Response, current_app, make_response, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from . import db, limiter, mail, csrf, cache
from .forms import OpcionForm, TamanoForm, ProductForm, UserProfileForm, LoginForm, RegistrationForm, ChangePasswordForm, PasswordRecoveryForm
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash  # Asegúrate de importar esto
from flask_mail import Message
import stripe
import os
from sqlalchemy.orm import joinedload
import xml.etree.ElementTree as ET
from urllib.parse import quote
from math import ceil
from sqlalchemy import func, case, and_
import logging
import re
import requests
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import boto3
from dotenv import load_dotenv
import jwt
from functools import wraps
from . import csrf
from flask import session


 

def init_routes(app):


    aws_access_key_id = os.environ.get('aws_access_key_id')
    aws_secret_access_key = os.environ.get('aws_secret_access_key')

    # Crear el cliente de S3 con las claves obtenidas
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name='us-east-1'
    )

    stripe.api_key = os.environ.get('STRIPE_API_KEY')

    def format_currency(value):
        return "${:,.2f}".format(value)

    # Registrar el filtro con Jinja2
    app.jinja_env.filters['currency'] = format_currency


    def token_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None

            if 'x-access-token' in request.headers:
                token = request.headers['x-access-token']

            if not token:
                current_app.logger.warning("Token faltante")
                return jsonify({'message': 'Token faltante'}), 401

            try:
                data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
                current_user = Usuario.query.get(data['user_id'])
                if not current_user:
                    current_app.logger.warning(f"Usuario no encontrado para el token: {token}")
                    return jsonify({'message': 'Usuario no encontrado'}), 401
            except jwt.ExpiredSignatureError:
                current_app.logger.warning("Token expirado")
                return jsonify({'message': 'El token ha expirado'}), 401
            except jwt.InvalidTokenError:
                current_app.logger.warning("Token inválido")
                return jsonify({'message': 'Token inválido'}), 401

            return f(current_user, *args, **kwargs)
        return decorated






#CAFFE menu-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    @app.route('/menu')
    def menu():
        productos = Producto.query.all()

        # En este enfoque, no creamos el pedido aquí. Solo lo haremos cuando el usuario seleccione un producto.
        # Esto evita pedidos vacíos si el usuario no compra.
        
        # Si no hay productos, se informa
        if not productos:
            flash('No hay productos disponibles en este momento.', 'info')
        
        # Intentamos cargar un pedido existente si lo hay
        pedido_id = session.get('pedido_id')
        pedido = Pedido.query.get(pedido_id) if pedido_id else None

        return render_template('pedidos/menu.html', productos=productos, pedido=pedido)


    @app.route('/seleccionar_tamano/<int:producto_id>', methods=['GET', 'POST'])
    def seleccionar_tamano(producto_id):
        # Primero, verificamos que el producto exista
        producto = Producto.query.get(producto_id)
        if not producto:
            flash('El producto seleccionado no existe.', 'warning')
            return redirect(url_for('menu'))

        # Ahora verificamos el pedido en la sesión
        pedido_id = session.get('pedido_id')
        if not pedido_id:
            # Si no hay pedido, lo creamos aquí, ya que el usuario muestra intención de comprar
            nuevo_pedido = Pedido(total=0.0, estado='en curso')
            db.session.add(nuevo_pedido)
            db.session.commit()
            session['pedido_id'] = nuevo_pedido.id
            pedido = nuevo_pedido
        else:
            pedido = Pedido.query.get(pedido_id)
            if not pedido:
                # Si el pedido no existe en la BD (caso raro), creamos uno nuevo
                nuevo_pedido = Pedido(total=0.0, estado='en curso')
                db.session.add(nuevo_pedido)
                db.session.commit()
                session['pedido_id'] = nuevo_pedido.id
                pedido = nuevo_pedido

        tamanos = Tamano.query.all()
        if not tamanos:
            flash('No hay tamaños disponibles.', 'info')
            return redirect(url_for('menu'))

        if request.method == 'POST':
            tamano_id = request.form.get('tamano_id')
            tamano = Tamano.query.get(tamano_id)
            if not tamano:
                flash('El tamaño seleccionado no existe.', 'warning')
                return redirect(url_for('menu'))

            producto_con_tamano = {
                "producto": producto.nombre,
                "tamano": tamano.nombre,
                "precio_base": producto.precio_base,
                "precio_tamano": tamano.precio_extra,
                "leche": None,
                "extras": [],
                "total": producto.precio_base + tamano.precio_extra
            }

            productos = pedido.productos or []
            productos.append(producto_con_tamano)
            pedido.productos = productos
            pedido.total += producto_con_tamano["total"]
            db.session.add(pedido)
            db.session.commit()
            return redirect(url_for('seleccionar_leche', producto_id=producto_id))

        return render_template('pedidos/seleccionar_tamano.html', producto=producto, tamanos=tamanos, pedido=pedido)


    @app.route('/seleccionar_leche/<int:producto_id>', methods=['GET', 'POST'])
    def seleccionar_leche(producto_id):
        pedido_id = session.get('pedido_id')
        if not pedido_id:
            flash('No tienes un pedido en curso.', 'warning')
            return redirect(url_for('menu'))

        pedido = Pedido.query.get(pedido_id)
        if not pedido or not pedido.productos:
            flash('No tienes productos en tu pedido.', 'warning')
            return redirect(url_for('menu'))

        producto = Producto.query.get(producto_id)
        if not producto:
            flash('El producto no existe.', 'warning')
            return redirect(url_for('menu'))

        producto_actual = pedido.productos[-1]
        tipos_de_leche = ['Entera', 'Deslactosada', 'Almendra', 'Soya']

        if request.method == 'POST':
            leche_seleccionada = request.form.get('leche')
            if not leche_seleccionada:
                flash('Debes seleccionar un tipo de leche.', 'warning')
                return redirect(url_for('seleccionar_leche', producto_id=producto_id))

            # Actualizar el producto con la leche elegida
            producto_actual["leche"] = leche_seleccionada

            # Reasignar y guardar
            productos = pedido.productos
            productos[-1] = producto_actual
            pedido.productos = productos

            db.session.add(pedido)
            db.session.commit()

            # Ahora pasamos a la selección de extras
            return redirect(url_for('seleccionar_extras', producto_id=producto_id))

        return render_template('pedidos/seleccionar_leche.html', pedido=pedido, tipos_de_leche=tipos_de_leche)


    @app.route('/seleccionar_extras/<int:producto_id>', methods=['GET', 'POST'])
    def seleccionar_extras(producto_id):
        pedido_id = session.get('pedido_id')
        if not pedido_id:
            flash('No tienes un pedido en curso.', 'warning')
            return redirect(url_for('menu'))

        pedido = Pedido.query.get(pedido_id)
        if not pedido or not pedido.productos:
            flash('No tienes productos en tu pedido.', 'warning')
            return redirect(url_for('menu'))

        producto = Producto.query.get(producto_id)
        if not producto:
            flash('El producto no existe.', 'warning')
            return redirect(url_for('menu'))

        producto_actual = pedido.productos[-1]
        extras_disponibles = ['Extra shot', 'Chocolate', 'Caramelo']

        if request.method == 'POST':
            extras = request.form.getlist('extras')
            costo_extra = len(extras) * 5.0

            # Actualizar extras y total
            producto_actual["extras"] = extras
            producto_actual["total"] += costo_extra

            # Reasignar y guardar
            productos = pedido.productos
            productos[-1] = producto_actual
            pedido.productos = productos
            pedido.total += costo_extra

            db.session.add(pedido)
            db.session.commit()

            if 'continuar' in request.form:
                return redirect(url_for('menu'))
            else:
                return redirect(url_for('resumen_pedido'))

        return render_template('pedidos/seleccionar_extras.html', pedido=pedido, extras_disponibles=extras_disponibles)


    @app.route('/resumen_pedido', methods=['GET', 'POST'])
    def resumen_pedido():
        pedido_id = session.get('pedido_id')
        if not pedido_id:
            flash('No tienes un pedido en curso.', 'warning')
            return redirect(url_for('menu'))

        pedido = Pedido.query.get(pedido_id)
        if not pedido or not pedido.productos:
            flash('Tu pedido está vacío.', 'info')
            return redirect(url_for('menu'))

        if request.method == 'POST':
            pedido.estado = "finalizado"
            db.session.commit()
            session.pop('pedido_id', None)
            flash('Pedido realizado con éxito', 'success')
            return redirect(url_for('menu'))

        return render_template('pedidos/resumen_pedido.html', pedido=pedido)



    @app.route('/eliminar_producto_pedido/<int:indice>', methods=['POST'])
    def eliminar_producto_pedido(indice):
        pedido_id = session.get('pedido_id')
        if not pedido_id:
            return redirect(url_for('menu'))

        pedido = Pedido.query.get_or_404(pedido_id)
        productos = pedido.productos  # Esto obtiene la lista actual
        
        if 0 <= indice < len(productos):
            # Remover el producto de la lista
            productos.pop(indice)
            pedido.productos = productos  # Reasignar para que se actualice productos_str
            # Recalcular el total
            nuevo_total = sum(p["total"] for p in productos)
            pedido.total = nuevo_total

            db.session.add(pedido)
            db.session.commit()

        return redirect(url_for('menu'))












#CAFFE dasbhoard-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    @app.route('/admin/dashboard', methods=['GET', 'POST'])
    @login_required
    def admin_dashboard():
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('index'))

        form = ProductForm()
        productos = Producto.query.all()  # Obtener todos los productos existentes

        if form.validate_on_submit():
            # Verificar si ya existe un producto con el mismo nombre
            producto_existente = Producto.query.filter_by(nombre=form.nombre.data).first()

            if producto_existente:
                flash(f"El producto '{form.nombre.data}' ya existe. No puedes agregar duplicados.", "danger")
            else:
                # Crear un nuevo producto
                nuevo_producto = Producto(
                    nombre=form.nombre.data,
                    descripcion=form.descripcion.data,
                    precio_base=form.precio_base.data
                )
                db.session.add(nuevo_producto)
                db.session.commit()

                flash("Producto agregado exitosamente.", "success")
                return redirect(url_for('admin_dashboard'))

        return render_template('admin/caffe.html', form=form, productos=productos)


    @app.route('/admin/eliminar_producto/<int:producto_id>', methods=['POST'])
    @login_required
    def eliminar_producto(producto_id):
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('index'))

        producto = Producto.query.get_or_404(producto_id)

        try:
            # Eliminar tamaños asociados si existen
            tamanos_asociados = Tamano.query.filter_by(producto_id=producto.id).all()
            for tamano in tamanos_asociados:
                db.session.delete(tamano)

            # Eliminar el producto
            db.session.delete(producto)
            db.session.commit()
            flash(f"Producto '{producto.nombre}' eliminado exitosamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Ocurrió un error al intentar eliminar el producto. Por favor, inténtalo nuevamente.", "danger")

        return redirect(url_for('admin_dashboard'))






    @app.route('/dashboard')
    @login_required
    def dashboard():
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('index'))
        return render_template('admin/dashboard.html')



    @app.route('/admin/tamanos', methods=['GET', 'POST'])
    @login_required
    def tamanos():
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('index'))

        form = TamanoForm()
        tamanos = Tamano.query.all()  # Carga todos los tamaños existentes

        if form.validate_on_submit():
            # Verifica si el tamaño ya existe
            tamano_existente = Tamano.query.filter_by(nombre=form.nombre.data).first()
            if tamano_existente:
                flash(f"El tamaño '{form.nombre.data}' ya existe. Si deseas modificarlo, primero elimínalo.", "warning")
            else:
                # Si no existe, lo agrega
                nuevo_tamano = Tamano(
                    nombre=form.nombre.data,
                    precio_extra=form.precio_extra.data
                )
                db.session.add(nuevo_tamano)
                db.session.commit()
                flash(f"Tamaño '{form.nombre.data}' agregado exitosamente.", "success")
            return redirect(url_for('tamanos'))

        return render_template('admin/tamanos.html', form=form, tamanos=tamanos)


    @app.route('/admin/tamanos/eliminar/<int:tamano_id>', methods=['POST'])
    @login_required
    def eliminar_tamano(tamano_id):
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('index'))

        tamano = Tamano.query.get_or_404(tamano_id)
        db.session.delete(tamano)
        db.session.commit()
        flash("Tamaño eliminado exitosamente.", "success")
        return redirect(url_for('tamanos'))






    @app.route('/admin/producto/<int:producto_id>/opciones', methods=['GET', 'POST'])
    @login_required
    def gestionar_opciones(producto_id):
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('index'))

        producto = Producto.query.get_or_404(producto_id)
        form = OpcionForm()

        if form.validate_on_submit():
            # Verificar si ya existe una opción con el mismo nombre y tipo para este producto
            opcion_existente = Opcion.query.filter_by(
                producto_id=producto.id,
                nombre=form.nombre.data,
                tipo=form.tipo.data
            ).first()

            if opcion_existente:
                flash(f"La opción '{form.nombre.data}' de tipo '{form.tipo.data}' ya existe.", "danger")
            else:
                nueva_opcion = Opcion(
                    producto_id=producto.id,
                    nombre=form.nombre.data,
                    tipo=form.tipo.data,
                    precio_extra=form.precio_extra.data
                )
                db.session.add(nueva_opcion)
                db.session.commit()
                flash("Opción agregada exitosamente.", "success")

            return redirect(url_for('gestionar_opciones', producto_id=producto.id))

        opciones = Opcion.query.filter_by(producto_id=producto.id).all()
        return render_template('admin/opciones.html', producto=producto, opciones=opciones, form=form)



    @app.route('/admin/opciones', methods=['GET', 'POST'])
    @login_required
    def opciones():
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('index'))

        # Opciones predefinidas para cada tipo
        opciones_por_tipo = {
            'Edulzante': ['Miel', 'Azúcar', 'Mascabada'],
            'Leche': ['Leche Entera', 'Leche de Soya', 'Leche de Almendras'],
            'Extra': ['Canela', 'Chocolate', 'Crema Batida']
        }

        form = OpcionForm()
        
        # Actualiza dinámicamente las opciones basadas en el tipo seleccionado
        if form.tipo.data in opciones_por_tipo:
            form.nombre.choices = [(opcion, opcion) for opcion in opciones_por_tipo[form.tipo.data]]
        else:
            form.nombre.choices = []

        if form.validate_on_submit():
            nueva_opcion = Opcion(
                nombre=form.nombre.data,
                tipo=form.tipo.data,
                precio_extra=form.precio_extra.data
            )
            db.session.add(nueva_opcion)
            db.session.commit()
            flash("Opción agregada exitosamente.", "success")
            return redirect(url_for('opciones'))

        opciones = Opcion.query.all()
        return render_template('admin/opciones.html', form=form, opciones=opciones)


    @app.route('/admin/opciones/dynamic/<tipo>', methods=['GET'])
    @login_required
    def obtener_opciones_dinamicas(tipo):
        # Opciones predefinidas para cada tipo
        opciones_por_tipo = {
            'Edulzante': ['Miel', 'Azúcar', 'Mascabada'],
            'Leche': ['Leche Entera', 'Leche de Soya', 'Leche de Almendras'],
            'Extra': ['Canela', 'Chocolate', 'Crema Batida']
        }

        # Obtén las opciones para el tipo solicitado
        opciones = opciones_por_tipo.get(tipo, [])

        # Devuelve las opciones como una respuesta JSON
        return jsonify(opciones)


    @app.route('/admin/eliminar_opcion/<int:opcion_id>', methods=['POST'])
    @login_required
    def eliminar_opcion(opcion_id):
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "danger")
            return redirect(url_for('index'))

        opcion = Opcion.query.get_or_404(opcion_id)

        try:
            db.session.delete(opcion)
            db.session.commit()
            flash(f"Opción '{opcion.nombre}' eliminada exitosamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Ocurrió un error al intentar eliminar la opción. Por favor, inténtalo nuevamente.", "danger")

        return redirect(url_for('opciones'))








#ARBSA----------------------------------------------------------------------------------------------------------------------
    @app.route('/api/api_delete_account', methods=['DELETE'])
    @token_required
    def api_delete_account(current_user):
        try:
            print(f"Eliminando usuario: {current_user.email}")
            db.session.delete(current_user)
            db.session.commit()
            logout_user()
            return jsonify({'message': 'Cuenta eliminada exitosamente'}), 200
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error al eliminar la cuenta: {e}")
            return jsonify({'message': 'Error al eliminar la cuenta', 'error': str(e)}), 500







    @app.route('/api/protected', methods=['GET'])
    @token_required
    def protected_route(current_user):
        app.logger.info(f"Encabezados recibidos: {request.headers}")
        return jsonify({'message': f'Bienvenido, {current_user.nombre_usuario}'})



    @app.route('/api/user_details', methods=['GET'])
    @token_required
    def user_details(current_user):
        try:
            current_app.logger.info(f"Detalles solicitados para el usuario: {current_user.email}")
            user_data = {
                'nombre_usuario': current_user.nombre_usuario,
                'es_administrador': current_user.es_administrador,
            }
            return jsonify(user_data), 200
        except Exception as e:
            current_app.logger.error(f"Error al obtener los detalles del usuario: {e}")
            return jsonify({'message': 'Error al obtener los detalles del usuario', 'error': str(e)}), 500



    @app.route('/api/api_login', methods=['POST'])
    @csrf.exempt  # Excluye CSRF para esta ruta
    def api_login():
        try:
            # Verifica que se envíen datos JSON válidos
            if not request.is_json:
                app.logger.error("Content-Type inválido o no es JSON")
                return jsonify({'message': 'Content-Type debe ser application/json'}), 415

            data = request.get_json()

            if not data:
                app.logger.error("Solicitud malformada: No se recibieron datos JSON")
                return jsonify({'message': 'Solicitud malformada: No se enviaron datos JSON'}), 400

            # Extrae el email y password
            email = data.get('email', '').strip().lower()  # Asegúrate de que no sea None
            password = data.get('password', '').strip()

            # Validaciones de campos obligatorios
            if not email or not password:
                app.logger.error("Faltan campos: email o contraseña")
                return jsonify({'message': 'El email y la contraseña son obligatorios'}), 400

            # Busca el usuario en la base de datos
            user = Usuario.query.filter(func.lower(Usuario.email) == email).first()

            if user and user.check_password(password):
                # Genera el token JWT si las credenciales son correctas
                token = jwt.encode({
                    'user_id': user.id,
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }, current_app.config['SECRET_KEY'], algorithm='HS256')

                app.logger.info(f"Usuario autenticado correctamente: {email}")
                return jsonify({
                    'access_token': token,
                    'es_administrador': user.es_administrador
                }), 200
            else:
                app.logger.warning(f"Intento de login con credenciales inválidas: {email}")
                return jsonify({'message': 'Correo o contraseña inválidos'}), 401

        except KeyError as ke:
            app.logger.error(f"Error de clave faltante en los datos JSON: {str(ke)}")
            return jsonify({'message': 'Solicitud malformada: Claves faltantes en los datos JSON'}), 400

        except Exception as e:
            # Captura cualquier error inesperado
            app.logger.error(f"Error interno en el login: {str(e)}")
            return jsonify({'message': 'Error interno del servidor'}), 500


    SUCURSALES = {
        1: '1-OBREGON',
        2: '2-NAVOJOA',
        3: '3-HUATABAMPO',
        4: '4-HERMOSILLO',
        5: '5-CASE',
        6: '6-CABORCA',
        7: '7-MEXICALI',
        8: '8-QUERETARO',
        9: '9-SAN JUAN DEL RIO',
        11: '11-MANEADERO'
    }

    CARTERAS = {
        1: '1-REFACCIONES Y ACEITES',
        2: '2-SERVICIO',
        3: '3-IMPLEMENTOS',
        4: '4-CHEQUES DEVUELTOS',
        5: '5-CNH CAPITAL',
        6: '6-MAQUILAS',
        7: '7-MAQUINARIA DOLARES',
        8: '8-NO USAR COMPLEM.',
        9: '9-MAQUINARIA EN DLS. FACT. M.N.',
        10: '10-FILIALES',
        11: '11-ARRENDAMIENTO',
        12: '12-REFACCIONES MINERIA',
        13: '13-MAQ. CONSTRUCCION M.N.',
        14: '14-MAQ. CONSTRUCC. DLS.',
        16: '16-TRACTORES M.N.',
        17: '17-TRACTORES DOLARES',
        19: '19-RENTA DE MAQUINARIA M.N.',
        20: '20-RENTA DE MAQUINARIA DLS.',
        21: '21-RENTAS MAQ. DLS',
        30: '30-OTRAS CXC',
        50: '50-CARTERA INCOBRABLE',
        51: '51-DEPOSITOS SIN IDENTIFICAR',
        99: '99-CONSOLIDADO'
    }

    @app.route('/api_detalle_cartera', methods=['GET'])
    def api_detalle_cartera():
        tipo_moneda = request.args.get('tipo_moneda', 'PESOS')
        sucursal_id = request.args.get('sucursal', type=int)
        cartera_id = request.args.get('cartera', type=int)
        dias_range = request.args.get('dias_range', type=str)

        if not sucursal_id or not cartera_id or not dias_range:
            return jsonify({"error": "sucursal, cartera y dias_range son parámetros requeridos"}), 400

        # Consulta inicial
        detalle_cartera = db.session.query(
            MiTabla.cod_cliente,
            MiTabla.nombre_cliente,
            MiTabla.dias_transcurridos,
            MiTabla.saldo_actual
        ).filter(
            MiTabla.sucursal == sucursal_id,
            MiTabla.cartera == cartera_id,
            MiTabla.tipo_moneda == tipo_moneda
        )

        # Aplicar filtro según el rango de días
        if dias_range == '1-30':
            detalle_cartera = detalle_cartera.filter(MiTabla.dias_transcurridos.between(1, 30))
        elif dias_range == '31-60':
            detalle_cartera = detalle_cartera.filter(MiTabla.dias_transcurridos.between(31, 60))
        elif dias_range == '61-90':
            detalle_cartera = detalle_cartera.filter(MiTabla.dias_transcurridos.between(61, 90))
        elif dias_range == '>90':
            detalle_cartera = detalle_cartera.filter(MiTabla.dias_transcurridos > 90)
        else:
            return jsonify({"error": "Rango de días inválido"}), 400

        # Ejecutar la consulta y convertir los resultados a JSON
        detalle_cartera = detalle_cartera.all()

        detalle_cartera_json = [
            {
                'cod_cliente': cliente.cod_cliente,
                'nombre_cliente': cliente.nombre_cliente,
                'dias_transcurridos': cliente.dias_transcurridos,
                'saldo_actual': float(cliente.saldo_actual)
            }
            for cliente in detalle_cartera
        ]

        return jsonify({
            'detalle_cartera': detalle_cartera_json
        })




    @app.route('/api_saldos-por-sucursal', methods=['GET'])
    def api_saldos_por_sucursal():
        tipo_moneda_seleccionada = request.args.get('tipo_moneda', 'PESOS')
        sucursal_seleccionada = request.args.get('sucursal', type=int)

        # Consulta principal por sucursal
        datos_sucursal = db.session.query(
            MiTabla.sucursal,
            func.sum(MiTabla.saldo_actual).label('saldo_total'),
            func.sum(
                case(
                    (MiTabla.dias_transcurridos <= 0, MiTabla.saldo_actual),
                    else_=0
                )
            ).label('saldo_no_vencido'),
            func.sum(
                case(
                    (and_(MiTabla.dias_transcurridos > 0, MiTabla.dias_transcurridos <= 30), MiTabla.saldo_actual),
                    else_=0
                )
            ).label('saldo_1_30'),
            func.sum(
                case(
                    (and_(MiTabla.dias_transcurridos > 30, MiTabla.dias_transcurridos <= 60), MiTabla.saldo_actual),
                    else_=0
                )
            ).label('saldo_31_60'),
            func.sum(
                case(
                    (and_(MiTabla.dias_transcurridos > 60, MiTabla.dias_transcurridos <= 90), MiTabla.saldo_actual),
                    else_=0
                )
            ).label('saldo_61_90'),
            func.sum(
                case(
                    (MiTabla.dias_transcurridos > 90, MiTabla.saldo_actual),
                    else_=0
                )
            ).label('saldo_91_mas')
        ).filter(
            MiTabla.tipo_moneda == tipo_moneda_seleccionada
        ).group_by(MiTabla.sucursal).all()

        # Calcular totales generales por columna en datos_sucursal
        total_saldo_total = sum([fila.saldo_total for fila in datos_sucursal])
        total_saldo_no_vencido = sum([fila.saldo_no_vencido for fila in datos_sucursal])
        total_saldo_1_30 = sum([fila.saldo_1_30 for fila in datos_sucursal])
        total_saldo_31_60 = sum([fila.saldo_31_60 for fila in datos_sucursal])
        total_saldo_61_90 = sum([fila.saldo_61_90 for fila in datos_sucursal])
        total_saldo_91_mas = sum([fila.saldo_91_mas for fila in datos_sucursal])

        # Formatear los datos en un diccionario para la respuesta JSON
        datos_sucursal_json = [
            {
                'sucursal': fila.sucursal,
                'saldo_total': float(fila.saldo_total),
                'saldo_no_vencido': float(fila.saldo_no_vencido),
                'saldo_1_30': float(fila.saldo_1_30),
                'saldo_31_60': float(fila.saldo_31_60),
                'saldo_61_90': float(fila.saldo_61_90),
                'saldo_91_mas': float(fila.saldo_91_mas)
            }
            for fila in datos_sucursal
        ]

        # Consulta secundaria por cartera si una sucursal está seleccionada
        datos_cartera_json = []
        if sucursal_seleccionada:
            datos_cartera = db.session.query(
                MiTabla.cartera,
                MiTabla.sucursal,
                func.sum(MiTabla.saldo_actual).label('saldo_total'),
                func.sum(
                    case(
                        (MiTabla.dias_transcurridos <= 0, MiTabla.saldo_actual),
                        else_=0
                    )
                ).label('saldo_no_vencido'),
                func.sum(
                    case(
                        (and_(MiTabla.dias_transcurridos > 0, MiTabla.dias_transcurridos <= 30), MiTabla.saldo_actual),
                        else_=0
                    )
                ).label('saldo_1_30'),
                func.sum(
                    case(
                        (and_(MiTabla.dias_transcurridos > 30, MiTabla.dias_transcurridos <= 60), MiTabla.saldo_actual),
                        else_=0
                    )
                ).label('saldo_31_60'),
                func.sum(
                    case(
                        (and_(MiTabla.dias_transcurridos > 60, MiTabla.dias_transcurridos <= 90), MiTabla.saldo_actual),
                        else_=0
                    )
                ).label('saldo_61_90'),
                func.sum(
                    case(
                        (MiTabla.dias_transcurridos > 90, MiTabla.saldo_actual),
                        else_=0
                    )
                ).label('saldo_91_mas')
            ).filter(
                MiTabla.sucursal == sucursal_seleccionada,
                MiTabla.tipo_moneda == tipo_moneda_seleccionada
            ).group_by(MiTabla.cartera, MiTabla.sucursal).all()

            datos_cartera_json = [
                {
                    'cartera': fila.cartera,
                    'sucursal': fila.sucursal,
                    'saldo_total': float(fila.saldo_total),
                    'saldo_no_vencido': float(fila.saldo_no_vencido),
                    'saldo_1_30': float(fila.saldo_1_30),
                    'saldo_31_60': float(fila.saldo_31_60),
                    'saldo_61_90': float(fila.saldo_61_90),
                    'saldo_91_mas': float(fila.saldo_91_mas)
                }
                for fila in datos_cartera
            ]

        # Respuesta en formato JSON
        return jsonify({
            'tipo_moneda': tipo_moneda_seleccionada,
            'sucursal_seleccionada': sucursal_seleccionada,
            'datos_sucursal': datos_sucursal_json,
            'totales': {
                'total_saldo_total': total_saldo_total,
                'total_saldo_no_vencido': total_saldo_no_vencido,
                'total_saldo_1_30': total_saldo_1_30,
                'total_saldo_31_60': total_saldo_31_60,
                'total_saldo_61_90': total_saldo_61_90,
                'total_saldo_91_mas': total_saldo_91_mas
            },
            'datos_cartera': datos_cartera_json,
            'nombresSucursales': SUCURSALES,
            'nombresCarteras': CARTERAS
        })









    @app.route('/aws')
    def aws():
        # Configura el bucket y el nombre del archivo en S3
        bucket_name = 's3-ventrua'
        file_key = 'DATOS/CARTERA.XLSX'

        try:
            # Descarga el archivo desde S3
            s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            file_content = s3_response['Body'].read()

            # Lee el archivo Excel desde el contenido descargado
            excel_data = pd.read_excel(BytesIO(file_content), header=3)

            # Resto del procesamiento de datos
            excel_data.columns = excel_data.columns.str.strip().str.upper()

            # Manejo de NaN y procesamiento de los datos
            excel_data['EMPRESA'] = excel_data['EMPRESA'].fillna(0).astype(int)
            excel_data['SUCURSAL'] = excel_data['SUCURSAL'].fillna(0).astype(int)
            excel_data['CARTERA'] = excel_data['CARTERA'].fillna(0).astype(int)
            excel_data['LLAVE SUC. DOC.'] = excel_data['LLAVE SUC. DOC.'].fillna('')
            excel_data['TIPO MOVIMIENTO'] = excel_data['TIPO MOVIMIENTO'].fillna('')
            excel_data['COD. CLIENTE'] = excel_data['COD. CLIENTE'].fillna('')
            excel_data['NOMBRE CLIENTE'] = excel_data['NOMBRE CLIENTE'].fillna('')
            excel_data['TIPO MONEDA'] = excel_data['TIPO MONEDA'].fillna('')
            excel_data['LÍMITE CRÉDITO'] = excel_data['LÍMITE CRÉDITO'].fillna(0)
            excel_data['IMPORTE ORIGINAL'] = excel_data['IMPORTE ORIGINAL'].fillna(0)
            excel_data['IMPORTE IVA'] = excel_data['IMPORTE IVA'].fillna(0)
            excel_data['TASA IVA'] = excel_data['TASA IVA'].fillna(0)
            excel_data['SALDO ACTUAL'] = excel_data['SALDO ACTUAL'].fillna(0)

            # Reemplazar NaN en fechas con una fecha por defecto
            fecha_defecto = datetime(1970, 1, 1)
            excel_data['FECHA DOCUMENTO'] = excel_data['FECHA DOCUMENTO'].apply(lambda x: x.date() if pd.notnull(x) else fecha_defecto.date())
            excel_data['FECHA VENCIMIENTO'] = excel_data['FECHA VENCIMIENTO'].apply(lambda x: x.date() if pd.notnull(x) else fecha_defecto.date())

            # Eliminar todos los registros existentes en la tabla
            db.session.query(MiTabla).delete()
            db.session.commit()

            # Filtrar los registros excluyendo las carteras 50 y 51, y facturas con SALDO ACTUAL menor a 8
            excel_data_filtrado = excel_data[
                (excel_data['CARTERA'] != 50) &
                (excel_data['CARTERA'] != 51) &
                (excel_data['SALDO ACTUAL'] >= 8)
            ]

            # Calcular los días de crédito como la diferencia entre FECHA VENCIMIENTO y FECHA DOCUMENTO
            excel_data_filtrado['DIAS CREDITO'] = excel_data_filtrado.apply(
                lambda row: (row['FECHA VENCIMIENTO'] - row['FECHA DOCUMENTO']).days, axis=1
            )

            # Calcular los días transcurridos considerando los días de crédito
            fecha_hoy = datetime.now().date()
            excel_data_filtrado['DIAS TRANSCURRIDOS'] = excel_data_filtrado.apply(
                lambda row: (fecha_hoy - row['FECHA DOCUMENTO']).days - row['DIAS CREDITO'], axis=1
            )

            # Insertar los nuevos datos
            for _, row in excel_data_filtrado.iterrows():
                nuevo_registro = MiTabla(
                    empresa=row['EMPRESA'],
                    llave_sucursal_doc=row['LLAVE SUC. DOC.'],
                    sucursal=row['SUCURSAL'],
                    cartera=row['CARTERA'],
                    tipo_movimiento=row['TIPO MOVIMIENTO'],
                    cod_cliente=row['COD. CLIENTE'],
                    nombre_cliente=row['NOMBRE CLIENTE'].strip(),
                    limite_credito=float(row['LÍMITE CRÉDITO']),
                    documento=row['DOCUMENTO'],
                    fecha_documento=row['FECHA DOCUMENTO'],
                    fecha_movimiento=row['FECHA VENCIMIENTO'],
                    dias_transcurridos=row['DIAS TRANSCURRIDOS'],
                    importe_original=float(row['IMPORTE ORIGINAL']),
                    importe_iva=float(row['IMPORTE IVA']),
                    tasa_iva=float(row['TASA IVA']),
                    saldo_actual=float(row['SALDO ACTUAL']),
                    tipo_moneda=row['TIPO MONEDA'].strip()
                )
                db.session.add(nuevo_registro)

            # Guardar todos los cambios
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Datos guardados correctamente'}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500




# Pagos:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    @app.route('/create-checkout-session-160', methods=['POST'])
    @csrf.exempt
    def create_checkout_session160():
        # Crear una sesión de checkout en Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_1Os3rAEtUmFFwNqbrqx6IJHy',  # Asegúrate de reemplazar esto con el ID de precio real de Stripe
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('web', _external=True),
        )
        return jsonify({'url': session.url})


    @app.route('/create-checkout-session-2399', methods=['POST'])
    @csrf.exempt
    def create_checkout_session2399():
        # Crear una sesión de checkout en Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_1Os46cEtUmFFwNqbFmal7IHr',  # Asegúrate de reemplazar esto con el ID de precio real de Stripe
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('web', _external=True),
        )
        return jsonify({'url': session.url})

    @app.route('/create-checkout-session-8980', methods=['POST'])
    @csrf.exempt
    def create_checkout_session8980():
        # Crear una sesión de checkout en Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_1Os46qEtUmFFwNqbW9dsVsp5',  # Asegúrate de reemplazar esto con el ID de precio real de Stripe
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('web', _external=True),
        )
        return jsonify({'url': session.url})

    @app.route('/success')
    def success():
        session_id = request.args.get('session_id')
        # Aquí puedes implementar la lógica que desees después de una suscripción exitosa,
        # como guardar la información en tu base de datos.
        return render_template('stripe/success.html')  # Muestra una página de éxito.

    @app.route('/cancel')
    def cancel():
        # Lógica en caso de que el usuario cancele la suscripción.
        return render_template('stripe/cancel.html')  # Muestra una página de cancelación.

    @app.route('/stripe-webhook', methods=['POST'])
    @csrf.exempt
    def stripe_webhook():
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')
        webhook_secret = os.environ.get('WEBHOOK_SECRET')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )

        except ValueError as e:
            # Si el payload es inválido, retorna un error 400
            return 'Invalid payload', 400
        except stripe.error.SignatureVerificationError as e:
            # Si la firma de la solicitud no es válida, retorna un error 400
            return 'Invalid signature', 400

        # Maneja el evento
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']  # Contiene la información del PaymentIntent
            # Haz algo con el payment_intent

        # Retorna una respuesta 200 para indicar a Stripe que el evento fue recibido correctamente
        return jsonify({'status': 'success'}), 200




# Rutas basicas:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    @app.route('/robots.txt')
    def static_from_root():
        return send_from_directory(app.static_folder, request.path[1:])



    @app.route('/sitemap_index.xml')
    def sitemap_index():
        base_url = "https://www.eridan123.com"
        sitemap_index = ET.Element('sitemapindex', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

        # Supongamos que divides tus productos en 6 sitemaps
        for i in range(1, 7):
            sitemap_element = ET.SubElement(sitemap_index, 'sitemap')
            loc = ET.SubElement(sitemap_element, 'loc')
            loc.text = f"{base_url}/sitemaps/sitemap_products_{i}.xml"

        sitemap_index_xml = ET.tostring(sitemap_index, encoding='UTF-8', method='xml')
        return Response(sitemap_index_xml, content_type='application/xml')





    @app.route('/')
    def index():
        return render_template('index.html')


    @app.route('/scraping')
    def scraping():
        return render_template('servicios/scraping.html')

    @app.route('/web')
    def web():
        return render_template('servicios/web.html')

    @app.route('/ecommerce')
    def ecommerce():
        return render_template('servicios/ecommerce.html')

    @app.route('/automatic')
    def automatic():
        return render_template('servicios/automatic.html')



    @app.route('/formulariocliente')
    def formulariocliente():
        return render_template('servicios/formulariocliente.html')



    @app.route('/team')
    def team():
        return render_template('team.html')

    @app.route('/about')
    def about():
        return render_template('footer/about.html')

    @app.route('/privacy')
    def privacy():
        return render_template('footer/privacy.html')

    @app.route('/aviso_cookies')
    def aviso_cookies():
        return render_template('footer/aviso_cookies.html')

    @app.route('/faq')
    def faq():
        return render_template('footer/faq.html')

    @app.route('/contact')
    def contact():
        return render_template('footer/contact.html')


    @app.route('/Investor')
    def Investor():
        return render_template('footer/investor.html')

    @app.route('/job')
    def job():
        return render_template('footer/job.html')

    @app.route('/termino')
    def termino():
        return render_template('footer/termino.html')





    @app.route('/send_contact_email', methods=['POST'])
    def send_contact_email():
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        msg = Message(f"Mensaje de {name}", recipients=['refacajeme@refacajeme.com'])
        msg.body = f"De: {name} <{email}>\n\n{message}"

        try:
            mail.send(msg)
            return jsonify({'status': 'success', 'message': 'Tu mensaje ha sido enviado. Gracias por contactarnos.'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Ocurrió un error al enviar el mensaje: {str(e)}'})

        return redirect(url_for('contact'))










# Gestión de Perfiles de Usuario:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    @app.route('/profile')
    @login_required
    def profile():
        return render_template('user/profile.html')


    @app.route('/recover_password', methods=['GET', 'POST'])
    def recover_password():
        form = PasswordRecoveryForm()
        if form.validate_on_submit():
            # Aquí iría la lógica para enviar un correo electrónico con instrucciones para restablecer la contraseña
            flash('Se han enviado instrucciones para restablecer tu contraseña a tu correo electrónico.', 'info')
            return redirect(url_for('login'))
        return render_template('user/recover_password.html', form=form)


    @app.route('/change_password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        form = ChangePasswordForm()
        if form.validate_on_submit():
            user = current_user
            if user.check_password(form.current_password.data):
                user.set_password(form.new_password.data)
                db.session.commit()
                flash('Tu contraseña ha sido actualizada.', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Contraseña actual incorrecta.', 'danger')
        return render_template('change_password.html', form=form)


    @app.route('/register', methods=['GET', 'POST'])
    @limiter.limit("50 per minute")
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        form = RegistrationForm()
        if form.validate_on_submit():
            # Comprobación de usuario existente
            email = form.email.data.lower()
            username = form.username.data.lower()
            existing_user = Usuario.query.filter(
                (func.lower(Usuario.email) == email) |
                (func.lower(Usuario.nombre_usuario) == username)
            ).first()

            if existing_user is None:
                hashed_password = generate_password_hash(form.password.data)
                user = Usuario(email=email, nombre_usuario=username, password_hash=hashed_password)
                db.session.add(user)
                db.session.commit()
                flash('Tu cuenta ha sido creada! Ahora puedes iniciar sesión', 'success')
                return redirect(url_for('login'))
            else:
                flash('Un usuario con ese correo electrónico o nombre de usuario ya existe')

        return render_template('user/register.html', title='Register', form=form)




    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit("50 per minute")
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = LoginForm()
        if form.validate_on_submit():
            user_input = form.username_or_email.data.lower()
            user = Usuario.query.filter(
                (func.lower(Usuario.email) == user_input) |
                (func.lower(Usuario.nombre_usuario) == user_input)
            ).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')  # Intenta redirigir a la página solicitada originalmente
                return redirect(next_page or url_for('index'))  # Si 'next' no existe, redirige a index
            else:
                flash('Por favor revisa el correo electrónico y la contraseña', 'danger')
        return render_template('user/login.html', title='Login', form=form)


    @app.route('/logout')
    @login_required  # Asegúrate de que solo los usuarios logueados puedan cerrar sesión
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/perfil/actualizar', methods=['GET', 'POST'])
    @login_required
    def actualizar_perfil():
        form = UserProfileForm(obj=current_user)
        if form.validate_on_submit():
            current_user.rfc = form.rfc.data
            current_user.telefono = form.telefono.data
            current_user.direccion = form.direccion.data
            db.session.commit()
            flash('Tu perfil ha sido actualizado.', 'success')
            return redirect(url_for('perfil'))
        return render_template('actualizar_perfil.html', form=form)





