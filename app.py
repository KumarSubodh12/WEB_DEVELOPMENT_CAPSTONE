import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# -------- MODELS --------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    image = db.Column(db.String(200))

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)

# -------- LOGIN --------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------- ROUTES --------

@app.route('/')
def dashboard():
    query = request.args.get('q')

    if query:
        products = Product.query.filter(Product.name.ilike(f"%{query}%")).all()
    else:
        products = Product.query.all()

    return render_template('dashboard.html', products=products)

# ❤️ WISHLIST
# ❤️ ADD TO WISHLIST
@app.route('/wishlist/<int:id>')
@login_required
def add_to_wishlist(id):
    item = Wishlist.query.filter_by(user_id=current_user.id, product_id=id).first()

    if not item:
        db.session.add(Wishlist(user_id=current_user.id, product_id=id))
        db.session.commit()

    return redirect('/wishlist')


# 📄 VIEW WISHLIST PAGE
@app.route('/wishlist')
@login_required
def wishlist_page():
    items = Wishlist.query.filter_by(user_id=current_user.id).all()
    products = [Product.query.get(i.product_id) for i in items]

    return render_template('wishlist.html', products=products)


# ❌ REMOVE FROM WISHLIST
@app.route('/remove_wishlist/<int:id>')
@login_required
def remove_wishlist(id):
    item = Wishlist.query.filter_by(user_id=current_user.id, product_id=id).first()

    if item:
        db.session.delete(item)
        db.session.commit()

    return redirect('/wishlist')
# 📦 CHECKOUT
@app.route('/checkout')
@login_required
def checkout():
    items = Cart.query.filter_by(user_id=current_user.id).all()

    for item in items:
        db.session.add(Order(user_id=current_user.id, product_id=item.product_id))
        db.session.delete(item)

    db.session.commit()
    flash("Order Placed Successfully 🎉")
    return redirect('/orders')
@app.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    products = [Product.query.get(o.product_id) for o in orders]

    return render_template('orders.html', products=products)
# 🧑‍💼 ADMIN PANEL (🔥 FIXED IMAGE SAVE)
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not current_user.is_authenticated:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        file = request.files['image']

        filename = secure_filename(file.filename)

        # 🔥 save in static/uploads
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 🔥 DB me clean path save (IMPORTANT FIX)
        image_path = 'uploads/' + filename

        product = Product(name=name, price=price, image=image_path)

        db.session.add(product)
        db.session.commit()

        return redirect('/admin')

    products = Product.query.all()
    return render_template('admin.html', products=products)

# ❌ DELETE
@app.route('/delete_product/<int:id>')
def delete_product(id):
    product = Product.query.get(id)
    if product:
        db.session.delete(product)
        db.session.commit()
    return redirect('/admin')

# ✏️ EDIT (🔥 FIXED)
@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    product = Product.query.get(id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.price = request.form['price']

        file = request.files['image']
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # 🔥 FIX
            product.image = 'uploads/' + filename

        db.session.commit()
        return redirect('/admin')

    return render_template('edit_product.html', product=product)

# 🔐 AUTH

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(email=request.form['email']).first():
            return "User already exists"

        user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()

        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect('/')

        return "Invalid credentials"

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

# 🛒 CART

@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    if not Cart.query.filter_by(user_id=current_user.id, product_id=id).first():
        db.session.add(Cart(user_id=current_user.id, product_id=id))
        db.session.commit()
    return redirect('/cart')

@app.route('/cart')
@login_required
def cart():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    products = [Product.query.get(i.product_id) for i in items]
    return render_template('cart.html', products=products)

# -------- INIT --------

def insert_products():
    pass  # ❌ remove dummy data

# -------- RUN --------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True, use_reloader=False)