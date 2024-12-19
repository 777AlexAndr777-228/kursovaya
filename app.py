from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sanechekBD.db'
db = SQLAlchemy(app)
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

class Sight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    info = db.Column(db.Text, nullable=False)
    adress = db.Column(db.Text)
    contac_info = db.Column(db.Text)
    dop_info = db.Column(db.Text)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    password = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sight_id = db.Column(db.Integer, db.ForeignKey('sight.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    sight = db.relationship('Sight', backref=db.backref('reviews', lazy=True))


class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    info = db.Column(db.Text, nullable=False)
    adress = db.Column(db.Text)
    contac_info = db.Column(db.Text)
    dop_info = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('suggestions', lazy=True))
    status = db.Column(db.String(50), default='pending')  # 'pending', 'approved', 'rejected'
    photo_path = db.Column(db.String(255))  # Путь к загруженной фотографии


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    sight_id = db.Column(db.Integer, db.ForeignKey('sight.id'), nullable=False)
    sight = db.relationship('Sight', backref=db.backref('events', lazy=True))



@app.route('/')
def index():
    sights = Sight.query.all()
    user = User.query.get(session.get('user')) if 'user' in session else None
    return render_template("index.html", sights=sights, user=user)

@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/register_form')
def register_form():
    return render_template('register_form.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['user'] = user.id
            session['user_status'] = user.status  # Сохраняем статус пользователя в сессии
            return redirect(url_for('index'))
        else:
            return "Invalid email or password"  # Add a better error message or redirect to login page with error
    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove the user from the session
    session.pop('user_status', None)  # Remove the user status from the session
    return redirect(url_for('index'))

@app.route('/sight/<int:sight_id>', methods=['GET', 'POST'])
def sight_detail(sight_id):
    sight = Sight.query.get_or_404(sight_id)
    events = Event.query.filter_by(sight_id=sight_id).all()  # Получаем события для данной достопримечательности
    if request.method == 'POST' and 'user' in session:
        review_text = request.form['review']
        user_id = session['user']
        new_review = Review(text=review_text, user_id=user_id, sight_id=sight_id)
        db.session.add(new_review)
        db.session.commit()
        return redirect(url_for('sight_detail', sight_id=sight_id))
    reviews = Review.query.filter_by(sight_id=sight_id).all()
    user = User.query.get(session.get('user')) if 'user' in session else None
    return render_template('sight_detail.html', sight=sight, reviews=reviews, events=events, user=user)


@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    if 'user' in session:
        user_id = session['user']
        user = User.query.get(user_id)
        if user.status == 'admin' or review.user_id == user_id:
            db.session.delete(review)
            db.session.commit()
            return redirect(url_for('sight_detail', sight_id=review.sight_id))
    return "You do not have permission to delete this review", 403

@app.route('/edit_review/<int:review_id>', methods=['GET', 'POST'])
def edit_review(review_id):
    review = Review.query.get_or_404(review_id)
    if 'user' in session:
        user_id = session['user']
        if review.user_id == user_id:
            if request.method == 'POST':
                review.text = request.form['review']
                db.session.commit()
                return redirect(url_for('sight_detail', sight_id=review.sight_id))
            return render_template('edit_review.html', review=review)
    return "You do not have permission to edit this review", 403








import os
from werkzeug.utils import secure_filename

# Укажите путь к папке для загрузки файлов
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Разрешенные расширения файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/suggest_sight', methods=['GET', 'POST'])
def suggest_sight():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        info = request.form['info']
        adress = request.form['adress']
        contac_info = request.form['contac_info']
        dop_info = request.form['dop_info']
        user_id = session['user']

        # Проверяем, загружен ли файл
        if 'photo' not in request.files:
            return "No file part"

        file = request.files['photo']

        # Если пользователь не выбрал файл
        if file.filename == '':
            return "No selected file"

        # Проверяем, что файл имеет допустимое расширение
        if file and allowed_file(file.filename):
            # Формируем имя файла на основе имени достопримечательности
            filename = secure_filename(f"{name.replace(' ', '_')}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            new_suggestion = Suggestion(
                name=name,
                info=info,
                adress=adress,
                contac_info=contac_info,
                dop_info=dop_info,
                user_id=user_id
            )
            db.session.add(new_suggestion)
            db.session.commit()
            return redirect(url_for('index'))

    return render_template('suggest_sight.html') 


@app.route('/admin/suggestions')
def admin_suggestions():
    # Проверяем, авторизован ли пользователь
    if 'user' not in session:
        return redirect(url_for('login'))

    # Получаем текущего пользователя
    user = User.query.get(session['user'])

    # Проверяем, является ли пользователь администратором
    if user.status != 'admin':
        return "You do not have permission to view this page", 403

    # Получаем все предложения со статусом 'pending'
    suggestions = Suggestion.query.filter_by(status='pending').all()

    # Передаем данные в шаблон
    return render_template('admin_suggestions.html', suggestions=suggestions)


@app.route('/admin/approve_suggestion/<int:suggestion_id>', methods=['POST'])
def approve_suggestion(suggestion_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user'])
    if user.status != 'admin':
        return "You do not have permission to perform this action", 403

    suggestion = Suggestion.query.get_or_404(suggestion_id)
    new_sight = Sight(
        name=suggestion.name,
        info=suggestion.info,
        adress=suggestion.adress,
        contac_info=suggestion.contac_info,
        dop_info=suggestion.dop_info
    )
    db.session.add(new_sight)
    db.session.delete(suggestion)
    db.session.commit()
    return redirect(url_for('admin_suggestions'))

@app.route('/admin/reject_suggestion/<int:suggestion_id>', methods=['POST'])
def reject_suggestion(suggestion_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user'])
    if user.status != 'admin':
        return "You do not have permission to perform this action", 403

    suggestion = Suggestion.query.get_or_404(suggestion_id)
    db.session.delete(suggestion)
    db.session.commit()
    return redirect(url_for('admin_suggestions'))

from datetime import datetime

# Пример корректной даты
correct_date = datetime(2025, 9, 23, 23, 9)  # Год, месяц, день, час, минута


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)