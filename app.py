import os
# from email import message
from flask import Flask, jsonify, render_template, request
from flask_jwt_extended import (JWTManager, create_access_token, jwt_required)# user management
from flask_mail import Mail, Message
from flask_marshmallow import Marshmallow  # serialization tata from instnces of clases to list of dictionaries for future jsonification
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Float, Integer, String

app = Flask(__name__) # instantiate flask application
basedir = os.path.dirname(__file__) # determine application root path
# assign DB URI in the same directory with the application. os.path.join used for correct represent path format in any OS.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'planet.db')
app.config['JWT_SECRET_KEY'] = 'some-secret-key'
# mailtrap configuration
app.config['MAIL_SERVER']='smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = '0b7fde58184de5'
app.config['MAIL_PASSWORD'] = '57afabd234215f'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False


# call SQLAlchemy constractor to instantiate our DB
db = SQLAlchemy(app)
# ma will used for serialize data extracted from DB(which is an object) to the format (list of dictionaries) which can be jsonified
ma = Marshmallow(app)
jwt = JWTManager(app)
mail = Mail(app)

# CLI (Command line interface) commands
# to create DB print "flask db_create" in the terminal (do not forget to create your working virtual enviriwment first)
@app.cli.command('db_create')
def db_create():
    db.create_all()
    print("============= DB created ============")

# to drop DB: "flask db_drop"
@app.cli.command('db_drop')
def db_drop():
    db.drop_all()
    print("============= DB dropped ==============")

# to seed DB: "flask db_seed"
@app.cli.command('db_seed')
def db_seed():
    # creating objects of class Planet
    mercury = Planet(planet_name='Mercury', planet_type='Class D', home_star='Sol', mass=3.258e23, radius=1516, distance=35.98e6)
    venus = Planet(planet_name='Venus', planet_type='Class K', home_star='Sol', mass=4.867e24, radius=3760, distance=67.24e6)
    earth = Planet(planet_name='Earth', planet_type='Class M', home_star='Sol', mass=5.972e24, radius=3959, distance=92.96e6)
    test_user = User(first_name="Dmytro", last_name="Ykv", email='test@test.com', password='password')
    # prepare to write those objects in to DB
    db.session.add(mercury)
    db.session.add(venus)
    db.session.add(earth)
    db.session.add(test_user)
    # commit all
    db.session.commit()
    print("============= DB seeded ============")

# http://127.0.0.1:5000/
@app.route('/')
def index():
    return render_template('index.html')

# http://127.0.0.1:5000/par?name=Dmytro&age=19
@app.route("/par")
def par():
    name = request.args.get('name')
    age = int(request.args.get('age'))
    if age < 18:
        return jsonify(message='Sorry, ' + name + ', you are too young'), 401
    return jsonify(message=name + '! Welcome to aduld club'), 200

# http://127.0.0.1:5000/arg/Dimon/19
@app.route("/arg/<string:name>/<int:age>")
def arg(name: str, age: int):
    if age < 18:
        return jsonify(message='Sorry, ' + name + ', you are too young'), 401
    return jsonify(message=name + '! Welcome to aduld club'), 200

# http://127.0.0.1:5000/planets
@app.route('/planets', methods=['GET'])
def planets():
    # result the query is a list of object type Planet. We can access to the fild, for example planets_list[0].planet_name
    planets_list = Planet.query.all()
    # planet_schema is instance a class PlanetSchema which inherit ma.Schema where ma is instanse of Marshmallow(app)
    # method dump allow to translate (serialize) data to list of dictionaries format which can be jsonityed   
    result = planets_schema.dump(planets_list)
    return jsonify(result)

@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    is_exist = User.query.filter_by(email=email).first()
    if is_exist:
        return jsonify(message='This email already existed'), 501

    user = User(first_name= request.form['first_name'], last_name= request.form['last_name'], email= request.form['email'], password= request.form['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify(message='User created'), 201

@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        email = request.json['email']
        password = request.json['password']
    else:
        email = request.form['email']
        password = request.form['password']
    is_exist = User.query.filter_by(email=email, password=password).first()
    if is_exist:
        access_token = create_access_token(identity=email)
        return jsonify(message="Login succeeded!", access_token=access_token)
    return jsonify(message='Wrong email or password'), 401
    
@app.route('/restore/<string:email>', methods=['GET'])
def restore(email: str):
    user = User.query.filter_by(email=email).first()
    if user:
        msg = Message('Your Planetary API password is ' + user.password, sender="admin@planetary.api", recipients=[email])
        mail.send(msg)
        return jsonify(message="Password sent to " + email)
    return jsonify(message="email does not exist"), 401

@app.route('/planet_info/<int:planet_id>', methods=['GET'])
def planet_info(planet_id: int):
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        result = planet_schema.dump(planet)
        return jsonify(result)
    return jsonify(message='Planet does not exist'), 404


@app.route('/add_planet', methods=['POST'])
@jwt_required()
def add_planet():
    planet_name = request.form['planet_name']
    home_star = request.form['home_star']
    
    is_exist = Planet.query.filter_by(planet_name=planet_name, home_star=home_star).first()
    
    if is_exist:
        return jsonify(message="Planet already exist"), 409
    
    planet = Planet(planet_name=planet_name, home_star=home_star,
                    planet_type=request.form['planet_type'], mass=float(request.form['mass']), radius=float(request.form['radius']), distance=float(request.form['distance']))
    db.session.add(planet)
    db.session.commit()
    return jsonify(message='Planet ' + planet_name + ' have been added')

@app.route('/update', methods=['PUT'])
@jwt_required()
def update():
    planet_id = request.form['planet_id']
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        planet.planet_name = request.form['planet_name']
        planet.home_star = request.form['home_star']
        planet.planet_type = request.form['planet_type']
        planet.mass=float(request.form['mass'])
        planet.radius=float(request.form['radius'])
        planet.distance=float(request.form['distance'])
        db.session.commit()
        return jsonify(message='Planet updated')
    return jsonify(message="There are no planet with id = " + planet_id), 404

@app.route('/remove_planet/<int:planet_id>', methods=['DELETE'])
@jwt_required()
def remove_planet(planet_id: int):
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        db.session.delete(planet)
        db.session.commit()
        return jsonify(message='Deleted planed with id = ' + str(planet_id)), 202
    return jsonify(message="There are no planet with id = " + str(planet_id)), 404


# db models. Classes represents DB tables
class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key = True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique = True)
    password = Column(String)

class Planet(db.Model):
    __tablename__ = 'planets'
    planet_id = Column(Integer, primary_key = True)
    planet_name = Column(String)
    planet_type = Column(String)
    home_star = Column(String)
    mass = Column(Float)
    radius = Column(Float)
    distance = Column(Float)

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first_name', "last_name", 'email', 'password')

class PlanetSchema(ma.Schema):
    class Meta:
        fields = ('planet_id', 'planet_name', 'planet_type', 'home_star', ' mass', 'radius', 'distance')

user_schema = UserSchema()
users_schema = UserSchema(many=True)

planet_schema = PlanetSchema()
planets_schema = PlanetSchema(many=True)

if __name__ =="__main__":
    app.run(debug=True)
