# C:\Users\Erick Lopez2\Desktop\eccomerce\app\app.py
from .models import Producto, Usuario, Cartitem, Cartsession, Order, OrderItem, ShippingAddress, MiTabla
from flask import Response, current_app, make_response, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from . import db, limiter, mail, csrf, cache  
from .forms import UserProfileForm, LoginForm, RegistrationForm, ChangePasswordForm, PasswordRecoveryForm
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash  # Asegúrate de importar esto
from flask_mail import Message
import stripe
from .email_functions import send_confirmation_email
import os 
from sqlalchemy.orm import joinedload
import xml.etree.ElementTree as ET
from urllib.parse import quote
from math import ceil
from sqlalchemy import func, case, and_
import logging
import re
import requests
from datetime import datetime
import pandas as pd
from io import BytesIO



def init_routes(app):
    stripe.api_key = os.environ.get('STRIPE_API_KEY')
    
    def format_currency(value):
        return "${:,.2f}".format(value)

    # Registrar el filtro con Jinja2
    app.jinja_env.filters['currency'] = format_currency





    @app.route('/download_and_process')
    def download_and_process():
        # URL del archivo Excel
        url = "http://app.gtepeyac.com/arbours/comercial/TMP/CONSOLIDADOS%20SALDOS%20DE%20CARTERA68267.XLSX"
        
        # Realiza la solicitud HTTP para descargar el archivo
        response = requests.get(url)
        if response.status_code == 200:
            try:
                # Lee el archivo Excel a partir de la fila 4 donde están los encabezados
                excel_data = pd.read_excel(BytesIO(response.content), header=3)
                
                # Limpia los nombres de las columnas
                excel_data.columns = excel_data.columns.str.strip().str.upper()

                # Manejo de NaN: reemplazar por valores por defecto
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
                excel_data['FECHA MOVIMIENTO'] = excel_data['FECHA MOVIMIENTO'].apply(lambda x: x.date() if pd.notnull(x) else fecha_defecto.date())

                # Eliminar todos los registros existentes en la tabla
                db.session.query(MiTabla).delete()
                db.session.commit()

                # Filtrar los registros excluyendo las carteras 50 y 51, y facturas con SALDO ACTUAL menor a 8
                excel_data_filtrado = excel_data[
                    (excel_data['CARTERA'] != 50) & 
                    (excel_data['CARTERA'] != 51) & 
                    (excel_data['SALDO ACTUAL'] >= 8)
                ]

                # Calcular los días de crédito como la diferencia entre FECHA MOVIMIENTO y FECHA DOCUMENTO
                excel_data_filtrado['DIAS CREDITO'] = excel_data_filtrado.apply(
                    lambda row: (row['FECHA MOVIMIENTO'] - row['FECHA DOCUMENTO']).days, axis=1
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
                        fecha_movimiento=row['FECHA MOVIMIENTO'],
                        dias_transcurridos=row['DIAS TRANSCURRIDOS'],  # Usando el valor calculado
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
        else:
            return jsonify({'status': 'error', 'message': 'Error al descargar el archivo'}), 400





























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



    @app.route('/api_saldos-por-sucursal')
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

        # Calcular totales generales por columna en `datos_sucursal`
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





# Historial de pedidos:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------




    @app.route('/order_history')
    @login_required
    def order_history():
        orders = Order.query.filter_by(user_id=current_user.id).all()
        return render_template('order_history.html', orders=orders)





    



# Carrito de Compras:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    @app.route('/cart/update/<int:product_id>', methods=['POST'])
    def update_cart(product_id):
        cart_item = None
        # Comprobar si el usuario está autenticado
        if current_user.is_authenticated:
            cart_item = Cartitem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        else:
            # Obtener el cartsession_id de las cookies
            cartsession_id = request.cookies.get('cartsession_id')
            if cartsession_id:
                cart_item = Cartitem.query.filter_by(cartsession=cartsession_id, product_id=product_id).first()

        if not cart_item:
            return jsonify({'status': 'error', 'message': 'Producto no encontrado en el carrito.'}), 404

        # Obtén los datos JSON de la solicitud
        data = request.json
        new_quantity = data.get('quantity')
        product = Producto.query.get(product_id)
        usuario = Usuario.query.get(current_user.id) if current_user.is_authenticated else None

        if new_quantity is None:
            return jsonify({'status': 'error', 'message': 'No se proporcionó cantidad.'}), 400
        
        try:
            new_quantity = int(new_quantity)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Cantidad inválida.'}), 400
        print("Nueva cantidad recibida:", new_quantity)

        # Obtener el producto
        product = Producto.query.get(product_id)
        if product is None:
            return jsonify({'status': 'error', 'message': 'Producto no encontrado.'}), 404

        # Ajustar la cantidad si es necesario
        if new_quantity > product.existencia:
            new_quantity = product.existencia
            message = f'Solo disponibles: {product.existencia}.'
            adjusted = True  # Indica que la cantidad fue ajustada
        else:
            message = 'Cantidad actualizada.'
            adjusted = False

        # Actualizar la cantidad y el subtotal
        if new_quantity > 0:
            cart_item.quantity = new_quantity
            # Calcula el nuevo subtotal
            precio_final_producto = product.calcular_precio_final(usuario)
            subtotal = new_quantity * precio_final_producto
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': message,
                'price': precio_final_producto,
                'new_quantity': new_quantity,
                'adjusted': adjusted,
                'subtotal': subtotal  # Enviar subtotal basado en precio final
            })
        else:
            return jsonify({'status': 'success', 'new_quantity': new_quantity, 'subtotal': subtotal})



    @app.route('/cart/add', methods=['POST'])
    def add_to_cart():
        id_producto = request.form.get('id_producto', type=int)
        quantity = request.form.get('quantity', type=int)

        if not id_producto or not quantity:
            return jsonify({'status': 'error', 'message': 'Faltan datos del producto o la cantidad.'})

        product = Producto.query.get(id_producto)
        if not product:
            return jsonify({'status': 'error', 'message': 'El producto no existe.'})

        if quantity > product.existencia:
            return jsonify({'status': 'error', 'message': 'No hay suficiente stock del producto.'})

        # Comprobar si el usuario está autenticado o no
        if current_user.is_authenticated:
            user_id = current_user.id
            cartsession_id = None
        else:
            # Para usuarios no autenticados, usar una sesión de carrito
            cartsession_id = request.cookies.get('cartsession_id')
            if not cartsession_id:
                cartsession = Cartsession()  # Crea una nueva sesión de carrito
                db.session.add(cartsession)
                db.session.commit()
                cartsession_id = cartsession.id

        # Intenta encontrar un elemento existente en el carrito
        cart_item = Cartitem.query.filter_by(
            cartsession=cartsession_id,
            user_id=current_user.id if current_user.is_authenticated else None,
            product_id=id_producto
        ).first()

        total_quantity = quantity
        if cart_item:
            total_quantity += cart_item.quantity

        if total_quantity > product.existencia:
            return jsonify({'status': 'error', 'message': 'No hay suficiente stock del producto. Solo quedan ' + str(product.existencia) + ' unidades disponibles.'})

        if cart_item:
            cart_item.quantity = min(total_quantity, product.existencia)
        else:
            new_cart_item = Cartitem(
                product_id=id_producto,
                quantity=quantity,
                user_id=current_user.id if current_user.is_authenticated else None,
                cartsession=cartsession_id if not current_user.is_authenticated else None
            )
            db.session.add(new_cart_item)

        try:
            db.session.commit()

            # Preparar y enviar respuesta
            response = make_response(jsonify({'status': 'success', 'message': 'Producto añadido al carrito'}))
            if cartsession_id:  # Si es un usuario no registrado, establece la cookie
                response.set_cookie('cartsession_id', cartsession_id, max_age=7*24*60*60)  # Expira en 7 días
            return response

        except Exception as e:
            db.session.rollback()
            print(f"Error al añadir al carrito: {e}, Producto: {id_producto}")
            return jsonify({'status': 'error', 'message': 'Ocurrió un error al añadir el producto al carrito.'})





    @app.route('/cart/remove/<int:product_id>', methods=['POST'])
    def remove_from_cart(product_id):
        if current_user.is_authenticated:
            user_id = current_user.id
            cart_item = Cartitem.query.filter_by(user_id=user_id, product_id=product_id).first()
        else:
            cartsession_id = request.cookies.get('cartsession_id')
            if cartsession_id:
                cart_item = Cartitem.query.filter_by(cartsession=cartsession_id, product_id=product_id).first()
            else:
                return jsonify({'status': 'error', 'message': 'Producto no encontrado en el carrito.'}), 404

        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Producto eliminado del carrito.', 'success')
        else:
            flash('Producto no encontrado en el carrito.', 'error')

        return redirect(url_for('view_cart'))



    @app.route('/api/cart/total')
    def get_cart_total():
        total = 0
        if current_user.is_authenticated:
            cart_items = Cartitem.query.filter_by(user_id=current_user.id).all()
        else:
            cartsession_id = request.cookies.get('cartsession_id')
            if cartsession_id:
                cart_items = Cartitem.query.filter_by(cartsession=cartsession_id).all()
            else:
                cart_items = []

        for item in cart_items:
            product = Producto.query.get(item.product_id)
            if product:
                total += item.quantity * product.calcular_precio_final()
        return jsonify({'total': total})






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






# Sistema de Pedidos:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    @app.route('/checkout', methods=['GET', 'POST'])
    def checkout():
        if request.method == 'POST':
            # Recopilar información del formulario
            address = request.form.get('address')
            city = request.form.get('city')
            postal_code = request.form.get('postal_code')
            state = request.form.get('state')
            phone = request.form.get('phone')
            guest_email = request.form.get('guest_email') if not current_user.is_authenticated else None

            # Validar los campos requeridos
            if not all([address, city, postal_code, state]) or (not current_user.is_authenticated and not guest_email):
                flash('Por favor, completa todos los campos requeridos.', 'error')
                return redirect(url_for('checkout'))

            # Crear el pedido
            usuario_actual = current_user if current_user.is_authenticated else None
            if current_user.is_authenticated:
                order = Order(
                    user_id=current_user.id,
                    phone=phone,
                    status='Pendiente',
                    total=0  # Inicializar el total como 0
                )
            else:
                cartsession_id = request.cookies.get('cartsession_id')
                guest_email = request.form.get('guest_email') if not current_user.is_authenticated else None
                print("Guest Email: ", guest_email)  # Para propósitos de depuración

                order = Order(
                    guest_email=guest_email,
                    phone=phone,
                    status='Pendiente',
                    total=0,
                    cartsession_id=cartsession_id  # Asignar el cartsession_id para usuarios no registrados
                )

            db.session.add(order)
            db.session.flush()  # Para obtener el ID del pedido inmediatamente

            # Crear la dirección de envío
            shipping_address = ShippingAddress(
                order_id=order.id,
                address=address,
                city=city,
                postal_code=postal_code,
                state=state
            )
            db.session.add(shipping_address)

            # Convertir CartItem en OrderItem y calcular el total
            total = 0
            cart_items = Cartitem.query.filter_by(
                user_id=current_user.id if current_user.is_authenticated else None,
                cartsession=cartsession_id if not current_user.is_authenticated else None,
                order_id=None
            ).all()

            if not cart_items:
                flash('Tu carrito está vacío.', 'error')
                return redirect(url_for('view_cart'))

            for item in cart_items:
                producto = Producto.query.get(item.product_id)
                if producto:
                    precio_final = producto.calcular_precio_final(usuario_actual)

                    total += item.quantity * precio_final
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        price=precio_final 
                    )
                    db.session.add(order_item)

            order.total = total
            db.session.commit()

            # Redirigir a la página de pago
            return redirect(url_for('payment', order_id=order.id))

        return render_template('checkout.html', is_authenticated=current_user.is_authenticated)




    @app.route('/confirm_order/<int:order_id>')
    def confirm_order(order_id):
        order = Order.query.get_or_404(order_id)
        order_items = OrderItem.query.filter_by(order_id=order.id).all()
        shipping_address = ShippingAddress.query.filter_by(order_id=order.id).first()

        # Calcular el precio final para cada item en el pedido
        total = 0
        for item in order_items:
            product = Producto.query.get(item.product_id)
            if product:
                item.precio_final = product.calcular_precio_final() * item.quantity
                total += item.precio_final  # Sumar al total

        if not (shipping_address and order_items):
            flash("Información de pedido incompleta.", "error")
            return redirect(url_for('index'))

        return render_template('confirm_order.html', order=order, order_items=order_items, shipping_address=shipping_address, total=total)







# Gestión de Productos-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

