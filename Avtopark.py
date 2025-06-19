import os
import csv
import logging
import re
from io import StringIO, BytesIO
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
import cloudinary
import cloudinary.uploader
import requests  # Додано для перевірки доступності URL
from dotenv import load_dotenv

load_dotenv()
cloudinary.config(secure=True)

# Налаштування логування
logging.basicConfig(filename='fleet.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "fallback-key")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "instance", "fleet.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

MAINTENANCE_TYPES = ["Планове ТО", "Заміна масла", "Діагностика", "Ремонт гальм", "Заміна шин", "Інше"]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')

class EventLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='event_logs')

class Manufacturer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    models = db.relationship('Model', backref='manufacturer', lazy=True)

class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    manufacturer_id = db.Column(db.Integer, db.ForeignKey('manufacturer.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=False)
    manufacturer_id = db.Column(db.Integer, db.ForeignKey('manufacturer.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('model.id'), nullable=False)
    year = db.Column(db.Integer)
    vin = db.Column(db.String(17), unique=True)
    mileage = db.Column(db.Integer, default=0)
    photo = db.Column(db.String(200))
    manufacturer = db.relationship('Manufacturer', backref='vehicles')
    model = db.relationship('Model', backref='vehicles')
    expenses = db.relationship('Expense', backref='expense_vehicle', lazy=True, cascade="all, delete-orphan")
    maintenances = db.relationship('Maintenance', backref='maintenance_vehicle', lazy=True, cascade="all, delete-orphan")
    insurances = db.relationship('Insurance', backref='insurance_vehicle', lazy=True, cascade="all, delete-orphan")

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    note = db.Column(db.String(200))
    receipt_photo = db.Column(db.String(200))
    is_archived = db.Column(db.Boolean, default=False)
    fuel_volume = db.Column(db.Float)
    fuel_price_per_liter = db.Column(db.Float)

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    mileage = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    note = db.Column(db.String(200))
    next_mileage = db.Column(db.Integer)

class Insurance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))

def init_db():
    with app.app_context():
        inspector = db.inspect(db.engine)
        if 'manufacturer' not in inspector.get_table_names() or 'user' not in inspector.get_table_names():
            db.create_all()
        if not Manufacturer.query.first():
            manufacturers = [
                ("Toyota", [
                    "Camry 2020", "Camry 2022 Hybrid", "Corolla 2019", "Corolla 2021", "RAV4 2020", "RAV4 2023 Hybrid"
                ]),
                ("Volkswagen", [
                    "Golf 2018", "Golf 2021 GTI", "Passat 2019", "Passat 2022", "Tiguan 2020", "Tiguan 2023 R-Line"
                ]),
                ("BMW", [
                    "3 Series 2019", "3 Series 2022 M340i", "5 Series 2020", "5 Series 2023", "X5 2019", "X5 2022 xDrive40e"
                ]),
                ("Ford", [
                    "Focus 2018", "Focus 2021 ST", "Fiesta 2019", "Fiesta 2020", "Mustang 2020", "Mustang 2023 Mach 1",
                    "Transit Connect 2019", "Transit Connect 2022 LWB", "Transit Connect 2023 Cargo Van"
                ]),
                ("Mercedes-Benz", [
                    "C-Class 2020", "C-Class 2023 AMG", "E-Class 2019", "E-Class 2022", "S-Class 2021", "S-Class 2023",
                    "Sprinter", "Sprinter 2019 Cargo Van", "Sprinter 2021 Crew Van", "Sprinter 2023 Passenger Van",
                    "Citan 2020", "Citan 2022 Tourer", "Citan 2023 Panel Van"
                ]),
                ("Renault", [
                    "Trafic 2019", "Trafic 2021 Passenger", "Trafic 2023 Cargo", "Kangoo 2020", "Kangoo 2022 Z.E.", "Kangoo 2023 Express"
                ]),
                ("Peugeot", [
                    "Partner 2019", "Partner 2021 Long", "Partner 2023 Electric", "Boxer 2020", "Boxer 2022 L3H2", "Boxer 2023 Van"
                ]),
                ("Fiat", [
                    "Ducato 2019", "Ducato 2021 Camper", "Ducato 2023 Cargo", "Panda 2020", "Panda 2022 Cross", "Panda 2023 Hybrid"
                ])
            ]
            for manufacturer_name, models in manufacturers:
                manufacturer = Manufacturer(name=manufacturer_name)
                db.session.add(manufacturer)
                db.session.flush()
                for model_name in models:
                    model = Model(name=model_name, manufacturer_id=manufacturer.id)
                    db.session.add(model)
            unknown_manufacturer = Manufacturer(name="Unknown")
            db.session.add(unknown_manufacturer)
            db.session.flush()
            unknown_model = Model(name="Unknown", manufacturer_id=unknown_manufacturer.id)
            db.session.add(unknown_model)
            db.session.commit()
            logging.info(f"База даних ініціалізована за шляхом: {app.config['SQLALCHEMY_DATABASE_URI']}")
        if not db.session.get(User, 1):
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            user1 = User(
                username='user1',
                password_hash=generate_password_hash('user123'),
                role='user'
            )
            db.session.add(admin)
            db.session.add(user1)
            db.session.commit()
            logging.info("Додано користувачів за замовчуванням: admin (admin123), user1 (user123)")
        else:
            logging.info("База даних уже ініціалізована, пропускаємо ініціалізацію.")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def predict_expenses(vehicle_id):
    expenses = Expense.query.filter_by(vehicle_id=vehicle_id).all()
    if len(expenses) < 2:
        return 0
    amounts = [expense.amount for expense in expenses]
    # Use the number of intervals between expenses when calculating
    # the average increase. Otherwise the predicted value will be
    # underestimated when more than two expenses exist.
    avg_increase = (amounts[-1] - amounts[0]) / (len(amounts) - 1)
    predicted = amounts[-1] + avg_increase
    return round(predicted, 2)

# Додано функцію для перевірки доступності URL
def is_url_accessible(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logging.error(f"Помилка перевірки доступності URL {url}: {str(e)}")
        return False


def upload_image(file):
    """Upload an image to Cloudinary and verify it is accessible."""
    try:
        upload_result = cloudinary.uploader.upload(file)
        logging.info(f"Cloudinary upload result: {upload_result}")
        secure_url = upload_result['secure_url']
        if not is_url_accessible(secure_url):
            logging.error(
                f"Завантажене зображення {secure_url} недоступне після завантаження"
            )
            raise Exception('Uploaded image is not accessible on Cloudinary!')
        return secure_url
    except Exception as e:
        logging.error(f"Помилка завантаження на Cloudinary: {str(e)}")
        raise


@app.template_filter('photo_url')
def photo_url(photo_path):
    """Return a usable URL for a photo path."""
    if not photo_path:
        return photo_path
    if photo_path.startswith('http'):
        return photo_path
    return url_for('static', filename=photo_path)

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Будь ласка, увійдіть у систему.", "error")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Будь ласка, увійдіть у систему.", "error")
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash("Доступ дозволено лише адміністраторам!", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.context_processor
def inject_globals():
    current_user = None
    if 'user_id' in session:
        current_user = db.session.get(User, session['user_id'])
    return dict(maintenance_types=MAINTENANCE_TYPES, current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash("Ви успішно увійшли!", "success")
            next_page = request.args.get('next') or url_for('index')
            return redirect(next_page)
        else:
            flash("Невірне ім'я користувача або пароль.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    flash("Ви вийшли з системи.", "success")
    return redirect(url_for('login'))

@app.route("/logs")
@app.route("/logs/<int:page>")
@login_required
@admin_required
def logs(page=1):
    per_page = 10
    logs_paginated = EventLog.query.order_by(EventLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs = logs_paginated.items
    return render_template("logs.html", logs=logs, logs_paginated=logs_paginated)

@app.route('/')
@app.route('/<int:page>')
@login_required
def index(page=1):
    per_page = 10
    search_query = request.args.get('search', '')
    query = Vehicle.query
    if search_query:
        query = query.filter(
            (Vehicle.license_plate.ilike(f'%{search_query}%')) |
            (Vehicle.vin.ilike(f'%{search_query}%')) |
            (Vehicle.manufacturer.has(Manufacturer.name.ilike(f'%{search_query}%'))) |
            (Vehicle.model.has(Model.name.ilike(f'%{search_query}%')))
        )

    vehicles_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    vehicles = vehicles_paginated.items
    manufacturers = Manufacturer.query.all()
    maintenances = Maintenance.query.all()
    notifications = []
    for vehicle in vehicles:
        vehicle_maintenances = [m for m in maintenances if m.vehicle_id == vehicle.id]
        upcoming_to = next((m for m in vehicle_maintenances if m.next_mileage and vehicle.mileage < m.next_mileage), None)
        if upcoming_to and vehicle.mileage >= upcoming_to.next_mileage - 1000:
            notifications.append(f"Автомобіль {vehicle.license_plate} наближається до ТО на {upcoming_to.next_mileage} км!")
        for insurance in vehicle.insurances:
            days_left = (insurance.end_date - datetime.utcnow().date()).days
            if 0 <= days_left <= 30:
                notifications.append(f"Страховка автомобіля {vehicle.license_plate} закінчується через {days_left} днів!")
    total_expenses = sum(expense.amount for expense in Expense.query.all())
    vehicle_count = len(Vehicle.query.all())
    return render_template('index.html', vehicles=vehicles, manufacturers=manufacturers, notifications=notifications, total_expenses=total_expenses, vehicle_count=vehicle_count, vehicles_paginated=vehicles_paginated, search_query=search_query)

@app.route('/reports')
@login_required
def reports():
    vehicles = Vehicle.query.all()
    expenses = Expense.query.all()
    maintenances = Maintenance.query.all()

    category_expenses = db.session.query(
        Expense.category, db.func.sum(Expense.amount).label('total')
    ).group_by(Expense.category).all()

    maintenance_stats = {}
    predicted_expenses = {}
    for vehicle in vehicles:
        vehicle_maintenances = [m for m in maintenances if m.vehicle_id == vehicle.id]
        maintenance_stats[vehicle.id] = {
            'count': len(vehicle_maintenances),
            'average_mileage': sum(m.mileage for m in vehicle_maintenances) / len(vehicle_maintenances) if vehicle_maintenances else 0,
            'upcoming_to': next((m for m in vehicle_maintenances if m.next_mileage and vehicle.mileage < m.next_mileage), None)
        }
        predicted_expenses[vehicle.id] = predict_expenses(vehicle.id)

    return render_template('reports.html', vehicles=vehicles, expenses=expenses,
                         category_expenses=category_expenses, maintenance_stats=maintenance_stats, predicted_expenses=predicted_expenses)

@app.route('/export_report', methods=['GET'])
@login_required
def export_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    vehicle_id = request.args.get('vehicle_id', type=int)

    query = Expense.query
    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, '%Y-%m-%d'))
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)

    expenses = query.all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Vehicle', 'Category', 'Amount', 'Date', 'Note'])
    for expense in expenses:
        writer.writerow([
            expense.expense_vehicle.license_plate,
            expense.category,
            expense.amount,
            expense.date.strftime('%Y-%m-%d'),
            expense.note or ''
        ])
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=report.csv'}
    )

@app.route('/export_report_pdf', methods=['GET'])
@login_required
def export_report_pdf():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    vehicle_id = request.args.get('vehicle_id', type=int)

    query = Expense.query
    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, '%Y-%m-%d'))
    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)
    expenses = query.all()

    maintenance_query = Maintenance.query
    if start_date:
        maintenance_query = maintenance_query.filter(Maintenance.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        maintenance_query = maintenance_query.filter(Maintenance.date <= datetime.strptime(end_date, '%Y-%m-%d'))
    if vehicle_id:
        maintenance_query = maintenance_query.filter_by(vehicle_id=vehicle_id)
    maintenances = maintenance_query.all()

    insurance_query = Insurance.query
    if vehicle_id:
        insurance_query = insurance_query.filter_by(vehicle_id=vehicle_id)
    insurances = insurance_query.all()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFillColor(Color(1, 0.38, 0))
    c.rect(50, 740, 500, 30, fill=True)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(Color(1, 1, 1))
    c.drawString(100, 750, "Nova Syla Auto Detailed Report")
    
    y = 700
    c.setFillColor(Color(0, 0, 0))
    c.setFont("Helvetica", 12)
    c.drawString(100, y, "Expenses:")
    y -= 20
    for expense in expenses:
        c.drawString(100, y, f"{expense.expense_vehicle.license_plate} - {expense.category}: {expense.amount} UAH ({expense.date.strftime('%Y-%m-%d')})")
        y -= 20
        if y < 50:
            c.showPage()
            y = 750

    y -= 20
    c.drawString(100, y, "Maintenances:")
    y -= 20
    for maintenance in maintenances:
        c.drawString(100, y, f"{maintenance.maintenance_vehicle.license_plate} - {maintenance.type}: {maintenance.mileage} km ({maintenance.date.strftime('%Y-%m-%d')})")
        y -= 20
        if y < 50:
            c.showPage()
            y = 750

    y -= 20
    c.drawString(100, y, "Insurances:")
    y -= 20
    for insurance in insurances:
        c.drawString(100, y, f"{insurance.insurance_vehicle.license_plate} - {insurance.company}: {insurance.amount} UAH ({insurance.start_date.strftime('%Y-%m-%d')} to {insurance.end_date.strftime('%Y-%m-%d')})")
        y -= 20
        if y < 50:
            c.showPage()
            y = 750

    c.showPage()
    c.save()
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=report.pdf'}
    )

@app.route('/vehicle/<int:vehicle_id>')
@login_required
def view_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id) or Vehicle.query.get_or_404(vehicle_id)
    predicted_expense = predict_expenses(vehicle_id)
    return render_template('vehicle.html', vehicle=vehicle, predicted_expense=predicted_expense)

@app.route('/add_vehicle', methods=['POST'])
def add_vehicle():
    # Перевірка авторизації
    if 'user_id' not in session:
        return jsonify({'error': 'Необхідно увійти в систему!'}), 401

    # Отримання даних із форми
    license_plate = request.form.get('license_plate')
    manufacturer_id = request.form.get('manufacturer')
    model_id = request.form.get('model')
    year = request.form.get('year')
    vin = request.form.get('vin')
    mileage = request.form.get('mileage')

    # Валідація даних
    if not license_plate or not mileage:
        return jsonify({'error': 'Номерний знак і пробіг обов’язкові!'}), 400

    if not Manufacturer.query.get(manufacturer_id) or not Model.query.get(model_id):
        return jsonify({'error': 'Виробник або модель не знайдені!'}), 400

    try:
        mileage = int(mileage)
        if mileage < 0:
            return jsonify({'error': 'Пробіг не може бути від’ємним!'}), 400
    except ValueError:
        return jsonify({'error': 'Пробіг має бути числом!'}), 400

    if vin and (len(vin) != 17 or not vin.isalnum()):
        return jsonify({'error': 'VIN-код має бути 17 символів із букв і цифр!'}), 400

    # Завантаження фото
    photo_path = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'error': 'Файл не вибрано!'}), 400

        if file.content_length > 5 * 1024 * 1024:  # Ліміт 5MB
            return jsonify({'error': 'Файл занадто великий (максимум 5MB)!'}), 400

        if file and allowed_file(file.filename):
            try:
                photo_path = upload_image(file)
            except Exception as e:
                return jsonify({'error': f'Помилка завантаження фото на Cloudinary: {str(e)}'}), 500

    # Створення нового автомобіля
    try:
        new_vehicle = Vehicle(
            license_plate=license_plate,
            manufacturer_id=manufacturer_id,
            model_id=model_id,
            year=year if year else None,
            vin=vin,
            mileage=mileage,
            photo=photo_path
        )
        db.session.add(new_vehicle)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Помилка збереження автомобіля: {str(e)}")
        return jsonify({'error': 'Помилка збереження автомобіля в базі даних!'}), 500

    # Логування події
    try:
        event = EventLog(
            user_id=session['user_id'],
            action="Додавання автомобіля",
            details=f"Додано автомобіль {license_plate}"
        )
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Помилка логування події: {str(e)}")
        return jsonify({'error': 'Помилка логування події!'}), 500

    return jsonify({'success': 'Автомобіль додано!', 'redirect': url_for('index')})

@app.route('/edit_vehicle/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id) or Vehicle.query.get_or_404(vehicle_id)
    if request.method == 'POST':
        try:
            old_license_plate = vehicle.license_plate
            vehicle.license_plate = request.form['license_plate'].strip()
            if not vehicle.license_plate:
                return "Помилка: Номерний знак не може бути порожнім!", 400

            vehicle.manufacturer_id = int(request.form['manufacturer'])
            vehicle.model_id = int(request.form['model'])
            vehicle.year = request.form['year']
            vehicle.vin = request.form['vin'].upper().strip()

            if len(vehicle.vin) != 17 or not vehicle.vin.isalnum():
                return "Помилка: VIN-код має бути 17 символів і складатися з букв та цифр!", 400

            if 'photo' in request.files:
                file = request.files['photo']
                if file and allowed_file(file.filename):
                    try:
                        vehicle.photo = upload_image(file)
                    except Exception as e:
                        return f"Помилка завантаження фото на Cloudinary: {str(e)}", 500

            db.session.commit()

            event = EventLog(
                user_id=session['user_id'],
                action="Редагування автомобіля",
                details=f"Відредаговано автомобіль {old_license_plate} -> {vehicle.license_plate}"
            )
            db.session.add(event)
            db.session.commit()

            logging.info(f"Відредаговано автомобіль {vehicle.license_plate} користувачем {session['username']} (IP: {request.remote_addr})")
            return redirect(url_for('index'))

        except Exception as e:
            logging.error(f"Помилка при редагуванні автомобіля {vehicle_id}: {str(e)}")
            return f"Помилка при редагуванні автомобіля: {str(e)}", 500

    manufacturers = Manufacturer.query.all()
    return render_template('edit_vehicle.html', vehicle=vehicle, manufacturers=manufacturers)

@app.route('/delete_vehicle/<int:vehicle_id>', methods=['POST'])
@login_required
@admin_required
def delete_vehicle(vehicle_id):
    try:
        vehicle = db.session.get(Vehicle, vehicle_id) or Vehicle.query.get_or_404(vehicle_id)
        license_plate = vehicle.license_plate

        # Видалення локального фото (хоча ми використовуємо Cloudinary, залишимо для сумісності)
        if vehicle.photo and not vehicle.photo.startswith('http'):
            filename = os.path.basename(vehicle.photo)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            try:
                real_file = os.path.realpath(file_path)
                real_folder = os.path.realpath(app.config['UPLOAD_FOLDER'])

                if os.path.commonprefix([real_file, real_folder]) == real_folder and os.path.exists(real_file):
                    os.remove(real_file)
            except Exception as file_err:
                logging.warning(f"Не вдалося видалити фото {file_path}: {file_err}")

        # Видалення об'єкта з БД
        db.session.delete(vehicle)
        db.session.commit()

        event = EventLog(
            user_id=session['user_id'],
            action="Видалення автомобіля",
            details=f"Видалено автомобіль {license_plate}"
        )
        db.session.add(event)
        db.session.commit()

        logging.info(f"Видалено автомобіль {license_plate} користувачем {session['username']} (IP: {request.remote_addr})")
        return redirect(url_for('index'))

    except Exception as e:
        logging.error(f"Помилка при видаленні автомобіля {vehicle_id}: {str(e)}")
        return f"Помилка при видаленні автомобіля: {str(e)}", 500

@app.route('/add_expense/<int:vehicle_id>', methods=['POST'])
@login_required
def add_expense(vehicle_id):
    try:
        category = request.form['category'].strip()
        amount_str = request.form['amount'].strip()
        note = request.form['note'].strip()
        expense_date_str = request.form.get('expense_date', '').strip()

        fuel_volume_str = request.form.get('fuel_volume', '0').strip()
        fuel_price_per_liter_str = request.form.get('fuel_price_per_liter', '0').strip()
        fuel_volume = None
        fuel_price_per_liter = None

        if expense_date_str:
            try:
                expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date()
                if expense_date > datetime.utcnow().date():
                    return jsonify({'error': "Дата витрати не може бути в майбутньому!"}), 400
            except ValueError:
                return jsonify({'error': "Невірний формат дати! Використовуйте YYYY-MM-DD."}), 400
        else:
            expense_date = datetime.utcnow().date()

        if category == 'Паливо':
            try:
                fuel_volume = float(fuel_volume_str) if fuel_volume_str else 0
                fuel_price_per_liter = float(fuel_price_per_liter_str) if fuel_price_per_liter_str else 0
                if fuel_volume < 0 or fuel_price_per_liter < 0:
                    return jsonify({'error': "Об'єм палива та ціна за літр не можуть бути від'ємними!"}), 400
                amount = fuel_volume * fuel_price_per_liter
                if amount <= 0:
                    return jsonify({'error': "Сума для палива має бути більшою за 0!"}), 400
            except ValueError:
                return jsonify({'error': "Об'єм палива та ціна за літр мають бути числами!"}), 400
        else:
            if not amount_str:
                return jsonify({'error': "Сума не може бути порожньою!"}), 400
            try:
                amount = float(amount_str)
                if amount <= 0:
                    return jsonify({'error': "Сума має бути більшою за 0!"}), 400
            except ValueError:
                return jsonify({'error': "Сума має бути числом!"}), 400

        receipt_photo_path = None
        if 'receipt_photo' in request.files:
            file = request.files['receipt_photo']
            if file and allowed_file(file.filename):
                try:
                    receipt_photo_path = upload_image(file)
                except Exception as e:
                    return jsonify({'error': f'Помилка завантаження фото чека на Cloudinary: {str(e)}'}), 500

        new_expense = Expense(
            vehicle_id=vehicle_id,
            category=category,
            amount=amount,
            date=expense_date,
            note=note if note else None,
            receipt_photo=receipt_photo_path,
            fuel_volume=fuel_volume,
            fuel_price_per_liter=fuel_price_per_liter
        )
        db.session.add(new_expense)
        db.session.commit()

        event = EventLog(
            user_id=session['user_id'],
            action="Додавання витрати",
            details=f"Додано витрату ({category}, {amount} грн, дата: {expense_date}) для автомобіля {vehicle_id}"
        )
        db.session.add(event)
        db.session.commit()

        logging.info(f"Додано витрату ({category}, {amount} грн, дата: {expense_date}) для автомобіля {vehicle_id} користувачем {session['username']} (IP: {request.remote_addr})")
        return jsonify({'success': 'Витрату успішно додано!', 'redirect': url_for('view_vehicle', vehicle_id=vehicle_id)})
    except Exception as e:
        logging.error(f"Помилка при додаванні витрати: {str(e)}")
        return jsonify({'error': f'Помилка при додаванні витрати: {str(e)}'}), 500

@app.route('/edit_expense/<int:expense_id>', methods=['POST'])
@login_required
def edit_expense(expense_id):
    try:
        expense = db.session.get(Expense, expense_id) or Expense.query.get_or_404(expense_id)
        old_category = expense.category
        old_amount = expense.amount

        expense.category = request.form['category'].strip()
        amount_str = request.form['amount'].strip()
        expense.note = request.form['note'].strip()

        if expense.category == 'Паливо':
            fuel_volume_str = request.form.get('fuel_volume', '0').strip()
            fuel_price_per_liter_str = request.form.get('fuel_price_per_liter', '0').strip()
            try:
                expense.fuel_volume = float(fuel_volume_str) if fuel_volume_str else 0
                expense.fuel_price_per_liter = float(fuel_price_per_liter_str) if fuel_price_per_liter_str else 0
                if expense.fuel_volume < 0 or expense.fuel_price_per_liter < 0:
                    return "Помилка: Об'єм палива та ціна за літр не можуть бути від'ємними!", 400
                expense.amount = expense.fuel_volume * expense.fuel_price_per_liter
                if expense.amount <= 0:
                    return "Помилка: Сума для палива має бути більшою за 0!", 400
            except ValueError:
                return "Помилка: Об'єм палива та ціна за літр мають бути числами!", 400
        else:
            if not amount_str:
                return "Помилка: Сума не може бути порожньою!", 400
            try:
                amount = float(amount_str)
                if amount <= 0:
                    return "Помилка: Сума має бути більшою за 0!", 400
                expense.amount = amount
                expense.fuel_volume = None
                expense.fuel_price_per_liter = None
            except ValueError:
                return "Помилка: Сума має бути числом!", 400

        if 'receipt_photo' in request.files:
            file = request.files['receipt_photo']
            if file and allowed_file(file.filename):
                try:
                    expense.receipt_photo = upload_image(file)
                except Exception as e:
                    return f"Помилка завантаження фото чека на Cloudinary: {str(e)}", 500

        db.session.commit()

        event = EventLog(
            user_id=session['user_id'],
            action="Редагування витрати",
            details=f"Відредаговано витрату ({old_category}, {old_amount} грн) -> ({expense.category}, {expense.amount} грн) для автомобіля {expense.vehicle_id}"
        )
        db.session.add(event)
        db.session.commit()

        logging.info(f"Відредаговано витрату ({expense.category}, {expense.amount} грн) для автомобіля {expense.vehicle_id} користувачем {session['username']} (IP: {request.remote_addr})")
        return redirect(url_for('view_vehicle', vehicle_id=expense.vehicle_id))

    except Exception as e:
        logging.error(f"Помилка при редагуванні витрати {expense_id}: {str(e)}")
        return f"Помилка при редагуванні витрати: {str(e)}", 500

@app.route('/archive_expense/<int:expense_id>', methods=['POST'])
@login_required
def archive_expense(expense_id):
    try:
        expense = db.session.get(Expense, expense_id) or Expense.query.get_or_404(expense_id)
        expense.is_archived = True
        db.session.commit()

        event = EventLog(
            user_id=session['user_id'],
            action="Архівування витрати",
            details=f"Архівовано витрату ({expense.category}, {expense.amount} грн) для автомобіля {expense.vehicle_id}"
        )
        db.session.add(event)
        db.session.commit()

        logging.info(f"Архівовано витрату ({expense.category}, {expense.amount} грн) для автомобіля {expense.vehicle_id} користувачем {session['username']} (IP: {request.remote_addr})")
        return redirect(url_for('view_vehicle', vehicle_id=expense.vehicle_id))
    except Exception as e:
        logging.error(f"Помилка при архівуванні витрати {expense_id}: {str(e)}")
        return f"Помилка при архівуванні витрати: {str(e)}", 500

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    try:
        expense = db.session.get(Expense, expense_id) or Expense.query.get_or_404(expense_id)
        vehicle_id = expense.vehicle_id
        category = expense.category
        amount = expense.amount
        if expense.receipt_photo:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(expense.receipt_photo))
            if os.path.exists(file_path):
                os.remove(file_path)
        db.session.delete(expense)
        db.session.commit()

        event = EventLog(
            user_id=session['user_id'],
            action="Видалення витрати",
            details=f"Видалено витрату ({category}, {amount} грн) для автомобіля {vehicle_id}"
        )
        db.session.add(event)
        db.session.commit()

        logging.info(f"Видалено витрату ({category}, {amount} грн) для автомобіля {vehicle_id} користувачем {session['username']} (IP: {request.remote_addr})")
        return redirect(url_for('view_vehicle', vehicle_id=vehicle_id))
    except Exception as e:
        logging.error(f"Помилка при видаленні витрати {expense_id}: {str(e)}")
        return f"Помилка при видаленні витрати: {str(e)}", 500

@app.route('/add_maintenance/<int:vehicle_id>', methods=['POST'])
@login_required
def add_maintenance(vehicle_id):
    try:
        vehicle = db.session.get(Vehicle, vehicle_id) or Vehicle.query.get_or_404(vehicle_id)
        mileage_str = request.form['mileage'].strip()
        type_to = request.form['type'].strip()
        note = request.form['note'].strip()
        next_mileage_str = request.form['next_mileage'].strip()

        if not mileage_str or not next_mileage_str:
            return "Помилка: Пробіг та наступне ТО не можуть бути порожніми!", 400

        try:
            mileage = int(mileage_str)
            next_mileage = int(next_mileage_str)
            if mileage < 0 or next_mileage < 0:
                return "Помилка: Пробіг та наступне ТО не можуть бути від'ємними!", 400
            if next_mileage <= mileage:
                return "Помилка: Наступне ТО має бути більшим за поточний пробіг!", 400
        except ValueError:
            return "Помилка: Пробіг та наступне ТО мають бути цілими числами!", 400

        vehicle.mileage = mileage

        new_maintenance = Maintenance(
            vehicle_id=vehicle_id,
            mileage=mileage,
            type=type_to,
            note=note if note else None,
            next_mileage=next_mileage
        )
        db.session.add(new_maintenance)
        db.session.commit()

        event = EventLog(
            user_id=session['user_id'],
            action="Додавання ТО",
            details=f"Додано ТО ({type_to}, {mileage} км) для автомобіля {vehicle_id}"
        )
        db.session.add(event)
        db.session.commit()

        logging.info(f"Додано ТО ({type_to}, {mileage} км) для автомобіля {vehicle_id} користувачем {session['username']} (IP: {request.remote_addr})")
        return redirect(url_for('view_vehicle', vehicle_id=vehicle_id))
    except Exception as e:
        logging.error(f"Помилка при додаванні ТО: {str(e)}")
        return f"Помилка при додаванні ТО: {str(e)}", 500

@app.route('/add_insurance/<int:vehicle_id>', methods=['POST'])
@login_required
def add_insurance(vehicle_id):
    try:
        company = request.form['company'].strip()
        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']
        amount_str = request.form['amount'].strip()
        note = request.form['note'].strip()

        if not company:
            return "Помилка: Назва компанії не може бути порожньою!", 400

        if not start_date_str or not end_date_str:
            return "Помилка: Дати початку та закінчення не можуть бути порожніми!", 400

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        if end_date <= start_date:
            return "Помилка: Дата закінчення має бути пізніше дати початку!", 400

        if not amount_str:
            return "Помилка: Сума не може бути порожньою!", 400

        try:
            amount = float(amount_str)
            if amount <= 0:
                return "Помилка: Сума має бути більшою за 0!", 400
        except ValueError:
            return "Помилка: Сума має бути числом!", 400

        new_insurance = Insurance(
            vehicle_id=vehicle_id,
            company=company,
            start_date=start_date,
            end_date=end_date,
            amount=amount,
            note=note if note else None
        )
        db.session.add(new_insurance)
        db.session.commit()

        new_expense = Expense(
            vehicle_id=vehicle_id,
            category="Страховка",
            amount=amount,
            note=f"Страховка від {company} ({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')})" if note else f"Страховка від {company}",
            date=datetime.utcnow()
        )
        db.session.add(new_expense)
        db.session.commit()

        event = EventLog(
            user_id=session['user_id'],
            action="Додавання страховки",
            details=f"Додано страховку ({company}, {amount} грн) та витрату для автомобіля {vehicle_id}"
        )
        db.session.add(event)
        db.session.commit()

        logging.info(f"Додано страховку ({company}, {amount} грн) та витрату для автомобіля {vehicle_id} користувачем {session['username']} (IP: {request.remote_addr})")
        flash("Страховку та відповідну витрату успішно додано!", "success")
        return redirect(url_for('view_vehicle', vehicle_id=vehicle_id))
    except Exception as e:
        db.session.rollback()
        logging.error(f"Помилка при додаванні страховки або витрати: {str(e)}")
        flash(f"Помилка при додаванні страховки: {str(e)}", "error")
        return redirect(url_for('view_vehicle', vehicle_id=vehicle_id))

@app.route('/delete_insurance/<int:insurance_id>', methods=['POST'])
@login_required
def delete_insurance(insurance_id):
    try:
        insurance = db.session.get(Insurance, insurance_id) or Insurance.query.get_or_404(insurance_id)
        vehicle_id = insurance.vehicle_id
        company = insurance.company
        amount = insurance.amount
        db.session.delete(insurance)
        db.session.commit()

        event = EventLog(
            user_id=session['user_id'],
            action="Видалення страховки",
            details=f"Видалено страховку ({company}, {amount} грн) для автомобіля {vehicle_id}"
        )
        db.session.add(event)
        db.session.commit()
        logging.info(f"Видалено страховку ({company}, {amount} грн) для автомобіля {vehicle_id} користувачем {session['username']} (IP: {request.remote_addr})")
        return redirect(url_for('view_vehicle', vehicle_id=vehicle_id))
    except Exception as e:
        logging.error(f"Помилка при видаленні страховки {insurance_id}: {str(e)}")
        return f"Помилка при видаленні страховки: {str(e)}", 500

@app.route('/get_models/<int:manufacturer_id>')
@login_required
def get_models(manufacturer_id):
    try:
        logging.debug(f"Отримання моделей для manufacturer_id: {manufacturer_id}")
        models = Model.query.filter_by(manufacturer_id=manufacturer_id).all()
        return jsonify([{'id': model.id, 'name': model.name} for model in models])
    except Exception as e:
        logging.error(f"Помилка при отриманні моделей для manufacturer_id {manufacturer_id}: {str(e)}")
        return jsonify({'error': 'Помилка при отриманні моделей'}), 500

@app.route('/add_manufacturer', methods=['POST'])
@login_required
@admin_required
def add_manufacturer():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        logging.debug(f"Спроба додати виробника: {name}")
        if not name:
            logging.warning("Назва виробника порожня")
            return jsonify({'error': 'Назва виробника не може бути порожньою'}), 400
        existing = Manufacturer.query.filter(db.func.lower(Manufacturer.name) == name.lower()).first()
        if existing:
            logging.info(f"Виробник '{name}' уже існує з ID: {existing.id}")
            return jsonify({'id': existing.id, 'name': existing.name, 'message': f'Виробник "{name}" уже існує'})
        manufacturer = Manufacturer(name=name)
        db.session.add(manufacturer)
        db.session.commit()
        event = EventLog(
            user_id=session['user_id'],
            action="Додавання виробника",
            details=f"Додано виробника {name}"
        )
        db.session.add(event)
        db.session.commit()
        logging.info(f"Додано виробника '{name}' з ID: {manufacturer.id}")
        return jsonify({'id': manufacturer.id, 'name': name, 'message': f'Виробник "{name}" успішно додано'})
    except Exception as e:
        logging.error(f"Помилка при додаванні виробника: {str(e)}")
        return jsonify({'error': f'Помилка при додаванні виробника: {str(e)}'}), 500

@app.route('/edit_manufacturer/<int:manufacturer_id>', methods=['POST'])
@login_required
@admin_required
def edit_manufacturer(manufacturer_id):
    try:
        manufacturer = db.session.get(Manufacturer, manufacturer_id) or Manufacturer.query.get_or_404(manufacturer_id)
        data = request.get_json()
        name = data.get('name', '').strip()
        logging.debug(f"Спроба редагувати виробника ID {manufacturer_id}: {name}")
        if not name:
            logging.warning("Назва виробника порожня")
            return jsonify({'error': 'Назва виробника не може бути порожньою'}), 400
        existing = Manufacturer.query.filter(
            db.func.lower(Manufacturer.name) == name.lower(),
            Manufacturer.id != manufacturer_id
        ).first()
        if existing:
            logging.info(f"Виробник '{name}' уже існує з ID: {existing.id}")
            return jsonify({'error': f'Виробник "{name}" уже існує'}), 400
        old_name = manufacturer.name
        manufacturer.name = name
        db.session.commit()
        event = EventLog(
            user_id=session['user_id'],
            action="Редагування виробника",
            details=f"Відредаговано виробника {old_name} -> {name}"
        )
        db.session.add(event)
        db.session.commit()
        logging.info(f"Відредаговано виробника ID {manufacturer_id} з '{old_name}' на '{name}'")
        return jsonify({'id': manufacturer.id, 'name': name, 'message': f'Виробник "{name}" успішно відредаговано'})
    except Exception as e:
        logging.error(f"Помилка при редагуванні виробника ID {manufacturer_id}: {str(e)}")
        return jsonify({'error': f'Помилка при редагуванні виробника: {str(e)}'}), 500

@app.route('/delete_manufacturer/<int:manufacturer_id>', methods=['POST'])
@login_required
@admin_required
def delete_manufacturer(manufacturer_id):
    try:
        manufacturer = db.session.get(Manufacturer, manufacturer_id) or Manufacturer.query.get_or_404(manufacturer_id)
        if manufacturer.name.lower() == "unknown":
            logging.warning("Спроба видалити виробника 'Unknown'")
            return jsonify({'error': 'Виробника "Unknown" не можна видалити'}), 400
        if manufacturer.vehicles:
            logging.warning(f"Виробник ID {manufacturer_id} має пов'язані автомобілі")
            return jsonify({'error': 'Виробник не може бути видалений, оскільки має пов’язані автомобілі'}), 400
        name = manufacturer.name
        db.session.delete(manufacturer)
        db.session.commit()
        event = EventLog(
            user_id=session['user_id'],
            action="Видалення виробника",
            details=f"Видалено виробника {name}"
        )
        db.session.add(event)
        db.session.commit()
        logging.info(f"Видалено виробника '{name}' з ID: {manufacturer_id}")
        return jsonify({'success': f'Виробник "{name}" успішно видалено'})
    except Exception as e:
        logging.error(f"Помилка при видаленні виробника ID {manufacturer_id}: {str(e)}")
        return jsonify({'error': f'Помилка при видаленні виробника: {str(e)}'}), 500

@app.route('/add_model', methods=['POST'])
@login_required
@admin_required
def add_model():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        manufacturer_id = data.get('manufacturer_id')
        logging.debug(f"Спроба додати модель: {name}, manufacturer_id: {manufacturer_id}")
        if not name or not manufacturer_id:
            logging.warning("Назва моделі або ID виробника порожні")
            return jsonify({'error': 'Назва моделі або ID виробника не можуть бути порожніми'}), 400
        manufacturer = db.session.get(Manufacturer, manufacturer_id)
        if not manufacturer:
            logging.warning(f"Виробник з ID {manufacturer_id} не знайдено")
            return jsonify({'error': 'Виробник не знайдений'}), 400
        existing = Model.query.filter(
            db.func.lower(Model.name) == name.lower(),
            Model.manufacturer_id == manufacturer_id
        ).first()
        if existing:
            logging.info(f"Модель '{name}' уже існує для manufacturer_id {manufacturer_id} з ID: {existing.id}")
            return jsonify({'id': existing.id, 'name': existing.name, 'message': f'Модель "{name}" уже існує'})
        model = Model(name=name, manufacturer_id=manufacturer_id)
        db.session.add(model)
        db.session.commit()
        event = EventLog(
            user_id=session['user_id'],
            action="Додавання моделі",
            details=f"Додано модель {name} для виробника ID {manufacturer_id}"
        )
        db.session.add(event)
        db.session.commit()
        logging.info(f"Додано модель '{name}' з ID: {model.id} для manufacturer_id: {manufacturer_id}")
        return jsonify({'id': model.id, 'name': name, 'message': f'Модель "{name}" успішно додано'})
    except Exception as e:
        logging.error(f"Помилка при додаванні моделі: {str(e)}")
        return jsonify({'error': f'Помилка при додаванні моделі: {str(e)}'}), 500

@app.route('/edit_model/<int:model_id>', methods=['POST'])
@login_required
@admin_required
def edit_model(model_id):
    try:
        model = db.session.get(Model, model_id) or Model.query.get_or_404(model_id)
        data = request.get_json()
        name = data.get('name', '').strip()
        manufacturer_id = data.get('manufacturer_id')
        logging.debug(f"Спроба редагувати модель ID {model_id}: {name}, manufacturer_id: {manufacturer_id}")
        if not name or not manufacturer_id:
            logging.warning("Назва моделі або ID виробника порожні")
            return jsonify({'error': 'Назва моделі або ID виробника не можуть бути порожніми'}), 400
        manufacturer = db.session.get(Manufacturer, manufacturer_id)
        if not manufacturer:
            logging.warning(f"Виробник з ID {manufacturer_id} не знайдено")
            return jsonify({'error': 'Виробник не знайдений'}), 400
        existing = Model.query.filter(
            db.func.lower(Model.name) == name.lower(),
            Model.manufacturer_id == manufacturer_id,
            Model.id != model_id
        ).first()
        if existing:
            logging.info(f"Модель '{name}' уже існує для manufacturer_id {manufacturer_id} з ID: {existing.id}")
            return jsonify({'error': f'Модель "{name}" уже існує для цього виробника'}), 400
        old_name = model.name
        model.name = name
        model.manufacturer_id = manufacturer_id
        db.session.commit()
        event = EventLog(
            user_id=session['user_id'],
            action="Редагування моделі",
            details=f"Відредаговано модель {old_name} -> {name} для виробника ID {manufacturer_id}"
        )
        db.session.add(event)
        db.session.commit()
        logging.info(f"Відредаговано модель ID {model_id} з '{old_name}' на '{name}'")
        return jsonify({'id': model.id, 'name': name, 'message': f'Модель "{name}" успішно відредаговано'})
    except Exception as e:
        logging.error(f"Помилка при редагуванні моделі ID {model_id}: {str(e)}")
        return jsonify({'error': f'Помилка при редагуванні моделі: {str(e)}'}), 500

@app.route('/delete_model/<int:model_id>', methods=['POST'])
@login_required
@admin_required
def delete_model(model_id):
    try:
        model = db.session.get(Model, model_id) or Model.query.get_or_404(model_id)
        if model.name.lower() == "unknown" and model.manufacturer.name.lower() == "unknown":
            logging.warning("Спроба видалити модель 'Unknown' виробника 'Unknown'")
            return jsonify({'error': 'Модель "Unknown" не можна видалити'}), 400
        if model.vehicles:
            logging.warning(f"Модель ID {model_id} має пов'язані автомобілі")
            return jsonify({'error': 'Модель не може бути видалена, оскільки має пов’язані автомобілі'}), 400
        name = model.name
        manufacturer_id = model.manufacturer_id
        db.session.delete(model)
        db.session.commit()
        event = EventLog(
            user_id=session['user_id'],
            action="Видалення моделі",
            details=f"Видалено модель {name} для виробника ID {manufacturer_id}"
        )
        db.session.add(event)
        db.session.commit()
        logging.info(f"Видалено модель '{name}' з ID: {model_id}")
        return jsonify({'success': f'Модель "{name}" успішно видалено'})
    except Exception as e:
        logging.error(f"Помилка при видаленні моделі ID {model_id}: {str(e)}")
        return jsonify({'error': f'Помилка при видаленні моделі: {str(e)}'}), 500

@app.route('/manage_manufacturers_models')
@login_required
@admin_required
def manage_manufacturers_models():
    manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
    models = Model.query.order_by(Model.name).all()
    return render_template('manage_manufacturers_models.html', manufacturers=manufacturers, models=models)

init_db()

if __name__ == '__main__':
    app.run()