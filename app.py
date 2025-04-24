
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

# Itinerary model
class Itinerary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(10), nullable=False)
    end_date = db.Column(db.String(10), nullable=False)
    destination = db.Column(db.String(100), nullable=True)
    budget = db.Column(db.Float, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='itineraries')

with app.app_context():
    db.session.execute(db.text('CREATE INDEX IF NOT EXISTS idx_itinerary_start_date ON itinerary (start_date);'))
    db.session.execute(db.text('CREATE INDEX IF NOT EXISTS idx_itinerary_end_date ON itinerary (end_date);'))
    db.create_all()

@app.route(
        '/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return "Username already exists"
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    itineraries = Itinerary.query.filter_by(user_id=session['user_id']).all()
    return render_template('index.html', itineraries=itineraries)

@app.route('/add', methods=['POST'])
def add_itinerary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    itinerary = Itinerary(
        name=request.form['name'],
        start_date=request.form['start_date'],
        end_date=request.form['end_date'],
        destination=request.form.get('destination'),
        budget=request.form.get('budget', type=float),
        user_id=session['user_id']
    )
    db.session.add(itinerary)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_itinerary(id):
    itinerary = Itinerary.query.filter_by(id=id, user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        itinerary.name = request.form['name']
        itinerary.start_date = request.form['start_date']
        itinerary.end_date = request.form['end_date']
        itinerary.destination = request.form.get('destination')
        itinerary.budget = request.form.get('budget', type=float)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit.html', itinerary=itinerary)
@app.route('/report')
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Prepare SQL for statistics
    base_query = '''
        SELECT 
            COUNT(*) as total_trips,
            AVG(julianday(end_date) - julianday(start_date)) as avg_duration,
            AVG(budget) as avg_budget
        FROM itinerary
        WHERE user_id = :user_id 
    '''
    conditions = []
    params = {"user_id": session['user_id']}

    if start_date:
        conditions.append("AND start_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("AND end_date <= :end_date")
        params["end_date"] = end_date

    final_query = base_query + " " + " ".join(conditions)
    result = db.session.execute(db.text(final_query), params).fetchone()
    total_trips = result[0] or 0
    avg_duration = result[1] or 0
    avg_budget = result[2] or 0

    # ORM query for display
    itinerary_query = Itinerary.query.filter_by(user_id=session['user_id'])
    if start_date:
        itinerary_query = itinerary_query.filter(Itinerary.start_date >= start_date)
    if end_date:
        itinerary_query = itinerary_query.filter(Itinerary.end_date <= end_date)

    itineraries = itinerary_query.all()

    return render_template('report.html',
                           total_trips=total_trips,
                           avg_duration=avg_duration,
                           avg_budget=avg_budget,
                           itineraries=itineraries)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_itinerary(id):
    itinerary = Itinerary.query.filter_by(id=id, user_id=session['user_id']).first_or_404()
    db.session.delete(itinerary)
    db.session.commit()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=5002)
