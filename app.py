import os
from flask import Flask, request, jsonify, url_for
from flasgger import Swagger
from dotenv import load_dotenv
from db_setup import db
from seller import Seller
from product import Product

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:3306/{os.getenv('MYSQL_DB')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)
Swagger(app)

@app.route('/')
def index():
    """
    Health Check
    ---
    responses:
      200:
        description: Seller Service is running
    """
    return 'Welcome to the Seller Service API!'

@app.route('/test-db-connection', methods=['GET'])
def test_db_connection():
    """
    Test the database connection
    ---
    responses:
      200:
        description: Database connected successfully
      500:
        description: Database connection error
    """
    try:
        sellers = Seller.query.all()
        return jsonify({"message": "Database connection successful", "sellers_count": len(sellers)}), 200
        #return 'Welcome to the Seller Service API!'
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/seller/register', methods=['POST'])
def register_seller():
    """
    Register a new seller
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            email:
              type: string
            password_hash:
              type: string
    responses:
      201:
        description: Seller created successfully
      400:
        description: Invalid input
    """
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password_hash = data.get('password_hash', 'default_hash_value')

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400

    # Check for duplicate seller
    if Seller.query.filter_by(email=email).first():
        return jsonify({"error": "Seller with this email already exists"}), 400

    # Create new seller
    new_seller = Seller(name=name, email=email, password_hash=password_hash)
    db.session.add(new_seller)
    db.session.commit()

    response = {
        "seller": new_seller.register_seller(),
        "_links": {
            "self": url_for('get_seller', seller_id=new_seller.seller_id, _external=True),
            "products": url_for('get_seller_products', seller_id=new_seller.seller_id, _external=True)
        }
    }
    return jsonify(response), 201

@app.route('/seller/<int:seller_id>', methods=['GET'])
def get_seller(seller_id):
    """
    Get seller details
    ---
    parameters:
      - name: seller_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: Seller details
      404:
        description: Seller not found
    """
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({"error": "Seller not found"}), 404

    seller_details = seller.get_details()
    seller_details["_links"] = {
        "self": url_for('get_seller', seller_id=seller_id, _external=True),
        "products": url_for('get_seller_products', seller_id=seller_id, _external=True)
    }
    return jsonify(seller_details), 200

@app.route('/seller/<int:seller_id>/products', methods=['GET'])
def get_seller_products(seller_id):
    """
    Get products for a given seller
    ---
    parameters:
      - name: seller_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: List of products
      404:
        description: Seller not found
    """
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({"error": "Seller not found"}), 404

    products = [p.get_details() for p in seller.products]
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
    """
    Create a new product
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            seller_id:
              type: integer
            name:
              type: string
            price:
              type: number
            stock:
              type: integer
            description:
              type: string
            category:
              type: string
    responses:
      201:
        description: Product created successfully
      400:
        description: Missing or invalid fields
      404:
        description: Seller not found
    """
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
        "product_id": new_product.id,
        "_links": {
            "self": url_for('get_product', product_id=new_product.id, _external=True),
            "seller": url_for('get_seller', seller_id=seller_id, _external=True)
        }
    }
    return jsonify(response), 201

@app.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    Get product details by product_id
    ---
    parameters:
      - name: product_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: Product details
      404:
        description: Product not found
    """
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    product_details = product.get_details()
    product_details["_links"] = {
        "self": url_for('get_product', product_id=product_id, _external=True),
        "seller": url_for('get_seller', seller_id=product.seller_id, _external=True)
    }
    return jsonify(product_details), 200

@app.route('/seller/<int:seller_id>/balance', methods=['GET'])
def get_seller_balance(seller_id):
    """
    Get seller's current balance
    ---
    parameters:
      - name: seller_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: Seller's current balance
      404:
        description: Seller not found
    """
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({"error": "Seller not found"}), 404

    return jsonify({"seller_id": seller.seller_id, "balance": seller.balance}), 200

@app.route('/seller/<int:seller_id>/balance', methods=['POST'])
def update_seller_balance(seller_id):
    """
    Update seller's balance
    ---
    parameters:
      - name: seller_id
        in: path
        required: true
        type: integer
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            amount:
              type: integer
    responses:
      200:
        description: Balance updated successfully
      404:
        description: Seller not found
      400:
        description: Invalid input
    """
    data = request.json
    amount = data.get('amount')

    if amount is None:
        return jsonify({"error": "Amount is required"}), 400

    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({"error": "Seller not found"}), 404

    seller.update_balance(amount)
    db.session.commit()

    return jsonify({"seller_id": seller.seller_id, "new_balance": seller.balance}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000, debug=True)
