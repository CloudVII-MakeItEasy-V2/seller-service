import os
from flask import Flask, request, jsonify, url_for
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000", "methods": ["GET", "POST", "PUT", "DELETE"]}})


app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:3306/{os.getenv('MYSQL_DB')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Seller(db.Model):
    __tablename__ = 'Seller'
    seller_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Integer, nullable=True)  # Ensure this matches your schema
    phone_number = db.Column(db.String(15), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    products = db.relationship('Product', backref='seller', lazy=True)

    def get_details(self):
        return {
            "seller_id": self.seller_id,
            "name": self.name,
            "email": self.email,
            "balance": self.balance,
            "phone_number": self.phone_number,
            "address": self.address
        }

class Product(db.Model):
    __tablename__ = 'Product'
    product_id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('Seller.seller_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200))
    category = db.Column(db.String(100))

    def update_stock(self, quantity_change):
        self.stock += quantity_change

    def get_details(self):
        return {
            'product_id': self.product_id,
            'name': self.name,
            'price': self.price,
            'stock': self.stock,
            'description': self.description,
            'category': self.category
        }

@app.route('/')
def index():
    return 'Seller Service Running!', 200

@app.route('/test-db-connection', methods=['GET'])
def test_db_connection():
    try:
        sellers = Seller.query.all()
        return jsonify({"message": "Database connection successful", "sellers_count": len(sellers)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/seller/register', methods=['POST'])
def register_seller():
    data = request.json

    # Extract all attributes from the request
    name = data.get('name')
    email = data.get('email')
    password_hash = data.get('password_hash')  # No default to enforce required input
    balance = data.get('balance', 0.0)  # Default balance is 0.0
    phone_number = data.get('phone_number', '')
    address = data.get('address', '')

    # Check for required fields
    if not email or not password_hash:
        return jsonify({"error": "Email and password are required"}), 400
    if not name:
        return jsonify({"error": "Name is required"}), 400

    # Check if the seller already exists
    existing_seller = Seller.query.filter_by(email=email).first()
    if existing_seller:
        return jsonify({"error": "Seller with this email already exists"}), 400

    # Create a new seller instance
    new_seller = Seller(
        name=name,
        email=email,
        password_hash=password_hash,
        balance=balance,
        phone_number=phone_number,
        address=address
    )

    # Save the new seller to the database
    db.session.add(new_seller)
    db.session.commit()

    # Construct the response
    response = {
        "seller": {
            "seller_id": new_seller.seller_id,
            "name": new_seller.name,
            "email": new_seller.email,
            "balance": new_seller.balance,
            "phone_number": new_seller.phone_number,
            "address": new_seller.address,
        },
        "_links": {
            "self": url_for('get_seller', seller_id=new_seller.seller_id, _external=True),
            "products": url_for('get_seller_products', seller_id=new_seller.seller_id, _external=True)
        }
    }

    return jsonify(response), 201


@app.route('/seller/<int:seller_id>', methods=['GET'])
def get_seller(seller_id):
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({"error": "Seller not found"}), 404

    # Include all attributes explicitly
    seller_details = {
        "seller_id": seller.seller_id,
        "name": seller.name,
        "email": seller.email,
        "password_hash": seller.password_hash,
        "balance": seller.balance,
        "phone_number": seller.phone_number,
        "address": seller.address,
    }

    # Add hypermedia links
    seller_details["_links"] = {
        "self": url_for('get_seller', seller_id=seller_id, _external=True),
        "products": url_for('get_seller_products', seller_id=seller_id, _external=True)
    }

    return jsonify(seller_details), 200


@app.route('/seller/<int:seller_id>/products', methods=['GET'])
def get_seller_products(seller_id):
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({"error": "Seller not found"}), 404
    products = [p.get_details() for p in seller.products]
    for p in products:
        p["_links"] = {
            "self": url_for('get_product', product_id=p['product_id'], _external=True),
            "seller": url_for('get_seller', seller_id=seller_id, _external=True)
        }
    response = {
        "seller_id": seller_id,
        "products": products,
        "_links": {
            "self": url_for('get_seller_products', seller_id=seller_id, _external=True),
            "seller": url_for('get_seller', seller_id=seller_id, _external=True)
        }
    }
    return jsonify(response), 200

@app.route('/product', methods=['POST'])
def create_product():
    data = request.json
    seller_id = data.get('seller_id')
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock')
    description = data.get('description')
    category = data.get('category')
    if not seller_id or not name or price is None or stock is None:
        return jsonify({"error": "seller_id, name, price, and stock are required"}), 400
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({"error": "Seller not found"}), 404
    new_product = Product(seller_id=seller_id, name=name, price=price, stock=stock, description=description, category=category)
    db.session.add(new_product)
    db.session.commit()
    response = {
        "message": "Product created successfully.",
        "product_id": new_product.product_id,
        "_links": {
            "self": url_for('get_product', product_id=new_product.product_id, _external=True),
            "seller": url_for('get_seller', seller_id=seller_id, _external=True)
        }
    }
    return jsonify(response), 201

@app.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    product_details = product.get_details()
    product_details["_links"] = {
        "self": url_for('get_product', product_id=product_id, _external=True),
        "seller": url_for('get_seller', seller_id=product.seller_id, _external=True)
    }
    return jsonify(product_details), 200

@app.route('/products', methods=['GET'])
def get_all_products():
    products = Product.query.all()
    products_list = []
    for p in products:
        d = p.get_details()
        d["_links"] = {
            "self": url_for('get_product', product_id=p.product_id, _external=True),
            "seller": url_for('get_seller', seller_id=p.seller_id, _external=True)
        }
        products_list.append(d)
    return jsonify(products_list), 200

@app.route('/product/update_stock', methods=['POST'])
def update_product_stock():
    data = request.json
    items = data.get('items', [])
    for it in items:
        product_id = it.get('product_id')
        quantity = it.get('quantity')
        if product_id and quantity is not None:
            product = Product.query.get(product_id)
            if product:
                product.update_stock(-quantity)
    db.session.commit()
    return jsonify({"message": "Stock updated successfully"}), 200

@app.route('/product/<int:product_id>', methods=['DELETE', 'OPTIONS'])
def delete_product(product_id):
    try:
        print(f"Received DELETE request for product_id: {product_id}")
        
        # Query the product
        product = Product.query.get(product_id)
        print(f"Product found: {product}")
        
        if not product:
            print("Product not found")
            return jsonify({"error": "Product not found"}), 404
        
        # Delete the product
        db.session.delete(product)
        db.session.commit()
        print(f"Deleted product with ID: {product_id}")
        
        return jsonify({"message": "Product deleted successfully."}), 200
    except Exception as e:
        # Rollback transaction in case of an error
        db.session.rollback()
        print(f"Error during delete: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/seller_management/<int:seller_id>', methods=['GET'])
def get_seller_dashboard(seller_id):
    try:
        # Query the seller by ID
        seller = Seller.query.get(seller_id)
        if not seller:
            return jsonify({"error": "Seller not found"}), 404

        # Construct the dashboard URL
        dashboard_url = f"https://dashboard.shipengine.com/?user_id={seller.seller_id}&name={seller.name.replace(' ', '%20')}"
        
        # Return the response
        return jsonify({
            "seller_id": seller.seller_id,
            "seller_name": seller.name,
            "dashboard_url": dashboard_url
        }), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/seller/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Find the seller by email
    seller = Seller.query.filter_by(email=email).first()
    if not seller:
        return jsonify({"error": "Invalid email or password"}), 401

    # Validate password (assuming you store a hashed password)
    if seller.password_hash != password:  # Replace this with a proper hash comparison (e.g., bcrypt check)
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({"seller_id": seller.seller_id, "message": "Login successful"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000, debug=True)
