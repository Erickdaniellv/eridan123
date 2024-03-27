from .models import Costoauto, Autos, Inversiones, SubastaVentura, Subastasusa, Traslados, Producto, Usuario, Cartitem, Cartsession, Order, OrderItem, ShippingAddress
from .forms import CostoAutoForm, UserProfileForm, AutoForm, InversionForm, LoginForm, RegistrationForm, ChangePasswordForm, PasswordRecoveryForm

from flask import Response, current_app, make_response, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from . import db, limiter, mail, csrf, cache  
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash  # Asegúrate de importar esto
from flask_mail import Message
import stripe
from .email_functions import send_confirmation_email
import os 
import xml.etree.ElementTree as ET
from urllib.parse import quote
from math import ceil
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging
import re, csv, sqlite3
from io import StringIO
import pandas as pd
import boto3



def init_routes(app):
    stripe.api_key = os.environ.get('STRIPE_API_KEY')
        
    def format_currency(value):
        try:
            # Intenta convertir el valor a float
            numeric_value = float(value)
        except ValueError:
            # Si la conversión falla, asume 0 como valor por defecto
            numeric_value = 0
        # Aplica el formato al valor numérico
        return "${:,.2f}".format(numeric_value)


    # Registrar el filtro con Jinja2
    app.jinja_env.filters['currency'] = format_currency





#ADMIN------------------------------------------------------------------------------------------------------------------------------------------------------------------

    @app.route('/admin/usuarios')
    @login_required
    def listar_usuarios():
        if not current_user.es_administrador:
            return "No tienes permiso para acceder a esta página", 403

        filtro = request.args.get('filtro', '')     
        if filtro:
            usuarios = Usuario.query.filter(
                db.or_(
                    Usuario.nombre_usuario.contains(filtro),
                    Usuario.email.contains(filtro),
                    Usuario.rfc.contains(filtro)
                )
            ).all()
        else:
            usuarios = Usuario.query.all()
        
        # Calcular la suma de inversiones para cada usuario
        suma_inversiones_por_usuario = {}
        for usuario in usuarios:
            suma_inversiones = db.session.query(db.func.sum(Inversiones.monto))\
                                .filter(Inversiones.usuario_id == usuario.id).scalar() or 0
            suma_inversiones_por_usuario[usuario.id] = suma_inversiones
        
        # Pasar tanto los usuarios como las sumas de inversiones al template
        return render_template('admin/client.html', usuarios=usuarios, suma_inversiones_por_usuario=suma_inversiones_por_usuario, filtro=filtro)



    @app.route('/cliente/<int:user_id>')
    @login_required
    def cliente_detalle(user_id):
        # Verificar si el usuario actual es administrador
        if not current_user.es_administrador:
            flash("No tienes permiso para acceder a esta página.", "warning")
            return redirect(url_for('index'))
        usuario = Usuario.query.get_or_404(user_id)
        # Aquí, agregar lógica para obtener autos asignados, inversiones y más información relacionada con el usuario.
        autos = Autos.query.filter_by(usuario_id=usuario.id).all()
        inversiones = Inversiones.query.filter_by(usuario_id=usuario.id).all()
        # Agregar cualquier otra información relevante que el administrador necesite visualizar
        
        return render_template('admin/idclient.html', usuario=usuario, autos=autos, inversiones=inversiones)





    @app.route('/registro-inversion/<int:user_id>', methods=['GET', 'POST'])
    @login_required
    def registro_inversion(user_id):
        usuario = Usuario.query.get_or_404(user_id)
        form = InversionForm()
        if form.validate_on_submit():
            inversion = Inversiones(
                descripcion=form.descripcion.data, 
                monto=form.monto.data,
                usuario_id=user_id  # Asegúrate de asignar la inversión al usuario correcto
            )
            db.session.add(inversion)
            db.session.commit()
            flash('Inversión registrada con éxito!', 'success')
            return redirect(url_for('listar_usuarios'))  # Asume que tienes una ruta 'index'
        return render_template('admin/registro_inversion.html', form=form, usuario=usuario)

    @app.route('/registro-auto/<int:user_id>', methods=['GET', 'POST'])
    @login_required
    def registro_auto(user_id):
        # Asegúrate de que el usuario actual es administrador o el mismo usuario que se está modificando
        if not current_user.es_administrador and current_user.id != user_id:
            flash("No tienes permiso para realizar esta acción.", "warning")
            return redirect(url_for('index'))

        usuario = Usuario.query.get_or_404(user_id)
        form = AutoForm()

        if form.validate_on_submit():
            auto = Autos(
                marca=form.marca.data, 
                modelo=form.modelo.data, 
                ano=form.ano.data, 
                vin=form.vin.data,
                usuario_id=user_id  # Aquí usas el user_id pasado a la función
            )
            db.session.add(auto)
            db.session.commit()
            flash('Auto registrado con éxito para ' + usuario.nombre_usuario, 'success')
            return redirect(url_for('listar_usuarios', user_id=user_id))

        return render_template('admin/registro_auto.html', form=form, usuario=usuario)






    @app.route('/agregar-costo/<int:auto_id>', methods=['GET', 'POST'])
    @login_required
    def agregar_costo(auto_id):
        auto = Autos.query.get_or_404(auto_id)
        form = CostoAutoForm()  # Inicializas el formulario aquí
        if form.validate_on_submit():
            # Recogiendo los datos del formulario
            costo_adquisicion = request.form.get('costo_adquisicion', type=float)
            costo_reparacion = request.form.get('costo_reparacion', type=float, default=0.0)
            costo_traslado = request.form.get('costo_traslado', type=float, default=0.0)
            costo_otros = request.form.get('costo_otros', type=float, default=0.0)
            costo_importacion = request.form.get('costo_importacion', type=float, default=0.0)
            costo_honorarios = request.form.get('costo_honorarios', type=float, default=0.0)
            costo_flete_obr = request.form.get('costo_flete_obr', type=float, default=0.0)
            costo_partes = request.form.get('costo_partes', type=float, default=0.0)
            costo_carrocero = request.form.get('costo_carrocero', type=float, default=0.0)
            costo_limpieza = request.form.get('costo_limpieza', type=float, default=0.0)
            costo_gasolina = request.form.get('costo_gasolina', type=float, default=0.0)
            costo_carlos = request.form.get('costo_carlos', type=float, default=0.0)
            costo_millas = request.form.get('costo_millas', type=float, default=0.0)

            # Creando el objeto Costoauto con todos los datos
            nuevo_costo = Costoauto(auto_id=auto.id, costo_adquisicion=costo_adquisicion,
                                    costo_reparacion=costo_reparacion, costo_traslado=costo_traslado,
                                    costo_otros=costo_otros, costo_importacion=costo_importacion,
                                    costo_honorarios=costo_honorarios, costo_flete_obr=costo_flete_obr,
                                    costo_partes=costo_partes, costo_carrocero=costo_carrocero,
                                    costo_limpieza=costo_limpieza, costo_gasolina=costo_gasolina,
                                    costo_carlos=costo_carlos, costo_millas=costo_millas)

            db.session.add(nuevo_costo)
            db.session.commit()
            flash('Costo agregado exitosamente', 'success')
            # Asegúrate de que estás redireccionando a la URL correcta después de agregar el costo
            return redirect(url_for('algun_endpoint', auto_id=auto.id))
            
        # Aquí es donde debes pasar el formulario a la plantilla
        return render_template('admin/costos.html', form=form, auto=auto)



#VINREPORTAUTO------------------------------------------------------------------------------------------------------------------------------------------------------------------
    






    @app.route('/update_database', methods=['GET'])
    def update_database_route():
        status, message = update_database_from_s3()
        return jsonify(message=message), status
    def update_database_from_s3():
        try:
            s3_client = boto3.client('s3', region_name='us-east-1')
            bucket_name = 's3-ventrua'
            csv_file_key = 'svdata.csv'
            
            csv_obj = s3_client.get_object(Bucket=bucket_name, Key=csv_file_key)
            csv_body = csv_obj['Body'].read().decode('utf-8')
            csv_reader = csv.DictReader(StringIO(csv_body))

            print("Comenzando la actualización de datos...")
            with current_app.app_context():
                # Desactivar autoflush
                db.session.autoflush = False
                
                for row in csv_reader:
                    existing_record = SubastaVentura.query.filter_by(vin=row['VIN']).first()
                    if existing_record:
                        # Aquí puedes decidir si actualizas el registro existente o simplemente continuas sin hacer nada
                        print(f"El VIN {row['VIN']} ya existe, se omite la inserción.")
                        continue  # Omite este registro y continúa con el siguiente


                    # Convertir las URLs de imágenes y documentos en strings
                    urlsimagenes_str = ','.join(row['URLs de Imágenes'].split(',')) 
                    urlsdocumentos_str = ','.join(row['URLs de Documentos'].split(','))
                    urlsimagenes3aws_str = ','.join(row['URLs de Imágenes3aws'].split(',')) 
                    urlsdocumentos3aws_str = ','.join(row['URLs de Documentos3aws'].split(','))

                    # Crear una nueva instancia de SubastaVentura
                    new_record = SubastaVentura(
                        vin=row['VIN'],
                        marca=row['Marca'],
                        modelo=row['Modelo'],
                        ano=row['Año'], 
                        precio_siniestro=row['Precio de Siniestro'],
                        fecha_subasta=row['Fecha de Subasta'],
                        condicion_venta=row['Condición de Venta'],
                        niu=row['NIU'],
                        vendedor=row['Vendedor'],
                        torre=row['Número de Subasta'],
                        ubicacion=row['Ubicación'],
                        color=row['Color'],
                        urlsimagenes=urlsimagenes_str,  
                        urlsdocumentos=urlsdocumentos_str,
                        urlsimagenes3aws=urlsimagenes3aws_str,  
                        urlsdocumentos3aws=urlsdocumentos3aws_str
                    )

                    # Utilizar merge() para actualizar o insertar el registro
                    db.session.merge(new_record)
                
                # Guardar todos los cambios en la base de datos
                db.session.commit()

            print("Actualización de datos completada.")
            return "Base de datos actualizada correctamente", 200
        
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error de integridad: {e}")
            return f"Error de integridad al actualizar la base de datos: {e}", 500
        except Exception as e:
            db.session.rollback()
            print(f"Ocurrió un error general: {e}")
            return f"Error al actualizar la base de datos: {e}", 500



    @app.route('/vehiculo/<vin>/')
    def vehiculo_detalle(vin):
        item = SubastaVentura.query.filter_by(vin=vin).first_or_404()
        if item is not None:
            return render_template('vehiculo_detalle.html', item=item)
        else:
            return "Vehículo no encontrado", 404
        

        

    @app.route('/sitemap.xml')
    def sitemap():
        items = SubastaVentura.query.all()
        
        sitemap_xml = render_template('sitemap.xml', items=items)
        response = make_response(sitemap_xml)
        response.headers['Content-Type'] = 'application/xml'
        
        return response
    
    @app.route('/robots.txt')
    def robots_txt():
        return send_from_directory(current_app.static_folder, 'robots.txt')


    @app.route('/property_car/<marca>/<modelo>/<int:ano>/<vin>/', methods=['GET'])
    def property_car(marca, modelo, ano, vin):
        item = SubastaVentura.query.filter_by(vin=vin, marca=marca, modelo=modelo, ano=ano).first()
        if item:
            return render_template('property_car.html', item=item)
        else:
            return "Vehículo no encontrado", 404


    @app.route('/data', methods=['GET'])
    def show_data():
        page = request.args.get('page', 1, type=int)  # Obtiene la página actual
        per_page = 10  # Define cuántos elementos quieres por página
        # Obtiene listas únicas de años, marcas y modelos para los filtros del formulario
        anos_unicos = db.session.query(SubastaVentura.ano).distinct().order_by(SubastaVentura.ano).all()
        marcas_unicas = db.session.query(SubastaVentura.marca).distinct().order_by(SubastaVentura.marca).all()
        modelos_unicos = db.session.query(SubastaVentura.modelo).distinct().order_by(SubastaVentura.modelo).all()

        # Extrae solo los valores (sin tuplas) para pasar al template
        anos_unicos = [ano[0] for ano in anos_unicos if ano[0] is not None]
        marcas_unicas = [marca[0] for marca in marcas_unicas if marca[0] is not None]
        modelos_unicos = [modelo[0] for modelo in modelos_unicos if modelo[0] is not None]

        # Aplicar filtros basados en la selección del usuario
        filters = {}
        for field in ['ano', 'marca', 'modelo']:
            value = request.args.get(field)
            if value:
                filters[field] = value
            
        query = SubastaVentura.query.filter_by(**filters) if filters else SubastaVentura.query
        paginated_data = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template('data.html', data=paginated_data, anos=anos_unicos, marcas=marcas_unicas, modelos=modelos_unicos)














    @app.route('/subastas')
    def subastas():
        return render_template('subastas.html')
    
    
    @app.route('/client')
    def client():
        return render_template('servicios/client.html')


    @app.route('/help')
    def help():
        return render_template('footer/help.html')


    @app.route('/traslados')
    def mostrar_traslados():
        datos_traslados = Traslados.query.all()
        return render_template('costes/traslados.html', traslados=datos_traslados)
        

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
                db.or_(
                    func.lower(Usuario.email) == email, 
                    func.lower(Usuario.nombre_usuario) == username
                )
            ).first()

            if existing_user:
                # Si encuentra un usuario existente, muestra un mensaje de error
                flash('Un usuario con ese correo electrónico o nombre de usuario ya existe.', 'error')
            else:
                # Si no encuentra un usuario, crea uno nuevo
                hashed_password = generate_password_hash(form.password.data)
                user = Usuario(email=email, nombre_usuario=username, password_hash=hashed_password)
                db.session.add(user)
                db.session.commit()
                flash('Tu cuenta ha sido creada! Ahora puedes iniciar sesión.', 'success')
                return redirect(url_for('login'))

        else:
            # Si el formulario no es válido, muestra mensajes de error para cada campo
            for fieldName, errorMessages in form.errors.items():
                for err in errorMessages:
                    flash(f'Error en {fieldName}: {err}', 'error')

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


