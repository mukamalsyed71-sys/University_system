from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-engine-key-xyz789' # Change this in production!

db_path = os.path.join(os.path.dirname(__file__), 'university.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

# ================= SYSTEM MODELS =================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='admin') # 'admin' or 'student'

class Student(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    major = db.Column(db.String(100), nullable=False)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    def to_dict(self): return {"id": self.id, "name": self.name, "major": self.major}

class Course(db.Model):
    code = db.Column(db.String(20), primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)
    def to_dict(self): return {"code": self.code, "title": self.title, "credits": self.credits}

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('student.id'), nullable=False)
    course_code = db.Column(db.String(20), db.ForeignKey('course.code'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= ROUTING & API GUARDRAILS =================

@app.route('/')
@login_required
def home():
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        
        return "<h1>Invalid Credentials. Try Again.</h1>", 401
    return '''
    <body style="background:#0f172a; color:#fff; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;">
        <form method="POST" style="background:rgba(255,255,255,0.05); padding:40px; border-radius:16px; border:1px solid rgba(255,255,255,0.1); width:300px; box-shadow:0 20px 25px -5px rgba(0,0,0,0.5)">
            <h2 style="margin-top:0; color:#818cf8;">UniVerse Login</h2>
            <input name="username" placeholder="Username (admin)" style="width:100%; padding:10px; margin-bottom:15px; border-radius:8px; border:1px solid #334155; background:#1e293b; color:#fff;" required><br>
            <input type="password" name="password" placeholder="Password (admin123)" style="width:100%; padding:10px; margin-bottom:20px; border-radius:8px; border:1px solid #334155; background:#1e293b; color:#fff;" required><br>
            <button type="submit" style="width:100%; padding:10px; border-radius:8px; border:none; background:#4f46e5; color:#fff; font-weight:bold; cursor:pointer;">Sign In</button>
        </form>
    </body>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))

# Secured APIs
@app.route('/api/students', methods=['GET', 'POST'])
@login_required
def manage_students():
    if request.method == 'POST':
        data = request.json
        if Student.query.get(data['id']): return jsonify({"error": "Exists"}), 400
        db.session.add(Student(id=data['id'], name=data['name'], major=data['major']))
        db.session.commit()
    return jsonify([s.to_dict() for s in Student.query.all()])

@app.route('/api/courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if request.method == 'POST':
        data = request.json
        if Course.query.get(data['code']): return jsonify({"error": "Exists"}), 400
        db.session.add(Course(code=data['code'], title=data['title'], credits=data['credits']))
        db.session.commit()
    return jsonify([c.to_dict() for c in Course.query.all()])

@app.route('/api/enrollments', methods=['GET', 'POST'])
@login_required
def manage_enrollments():
    if request.method == 'POST':
        data = request.json
        db.session.add(Enrollment(student_id=data['student_id'], course_code=data['course_code']))
        db.session.commit()
    return jsonify([{"student_name": e.student.name, "student_id": e.student_id, "course_title": e.course.title, "course_code": e.course_code} for e in Enrollment.query.all()])

# Create database and seed default administrative account safely
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        default_admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(default_admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)