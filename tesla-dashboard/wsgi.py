import threading
import json

from flask import Flask, session, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from geopy.geocoders import Nominatim

from tesla_api import TeslaAPI, TeslaAPIError
from worker import update_charge_worker

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////var/lib/tesla/tesla.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
with open('/var/lib/tesla/secret') as fp:
    app.secret_key = fp.read().strip()

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    access_token = db.Column(db.String(64))
    vehicles = db.relationship('Vehicle')


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    vin = db.Column(db.String(30))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    home_target = db.Column(db.Integer)
    away_target = db.Column(db.Integer)
    home_lat = db.Column(db.Integer)
    home_lon = db.Column(db.Integer)


db.create_all()

worker = threading.Thread(target=update_charge_worker, args=(User,))
worker.start()


@app.route("/")
def dashboard():
    if 'email' not in session:
        return redirect('/login')

    user = User.query.filter_by(email=session['email']).first()
    vehicles = TeslaAPI(user.access_token).vehicles()
    return render_template('index.html', user=user, vehicles=vehicles)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in request.form:
        try:
            cred = TeslaAPI().auth(
                request.form['email'],
                request.form.get('password')
            )
            session['email'] = request.form['email']

            user = User.query.filter_by(email=request.form['email']).first()
            if user:
                user.access_token = cred['access_token']
            else:
                user = User(
                    email=request.form['email'],
                    access_token=cred['access_token']
                )
                db.session.add(user)

            db.session.commit()

            return redirect('/')
        except TeslaAPIError:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/vehicles', methods=['POST'])
def vehicles():
    geolocator = Nominatim(user_agent="python3/tesla_dashboard")
    if 'home_address' in request.form:
        location = geolocator.geocode(request.form['home_address'])
    else:
        location = None
    user = User.query.filter_by(email=session['email']).first()
    vehicle_id = int(request.form['vehicle'])
    vehicles = dict((v['id'], v) for v in TeslaAPI(user.access_token).vehicles())

    if vehicle_id not in vehicles:
        print(request.form['vehicle'], vehicles)
        return redirect('/?error=Invalid+vehicle')

    for vehicle in user.vehicles:
        if vehicle.id == vehicle_id:
            vehicle.name = vehicles[vehicle_id]['display_name']
            vehicle.vin = vehicles[vehicle_id]['vin']
            vehicle.home_target = int(request.form['home_target'].strip('%'))
            vehicle.away_target = int(request.form['away_target'].strip('%'))
            if location:
                vehicle.home_lat = location.latitude
                vehicle.home_lon = location.longitude
            db.session.commit()
            return redirect('/?message=Vehicle+updated')

    if not location:
        return redirect('/?message=Please+specify+home+address')

    vehicle = Vehicle(
        id=request.form['vehicle'],
        name=vehicles[vehicle_id]['display_name'],
        vin=vehicles[vehicle_id]['vin'],
        user_id=user.id,
        home_target=int(request.form['home_target'].strip().strip('%')),
        away_target=int(request.form['away_target'].strip().strip('%')),
        home_lat=location.latitude,
        home_lon=location.longitude
    )
    db.session.add(vehicle)
    db.session.commit()

    return redirect('/?message=Vehicle+added')
