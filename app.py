import os
import json
from flask import Flask, request, jsonify, url_for, g
from flasgger import Swagger
from dotenv import load_dotenv
from db_setup import db
from seller import Seller
from product import Product
from functools import wraps
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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

# Service URLs
order_service_url = os.getenv('ORDER_SERVICE_URL', 'http://default-order-service-url')
seller_service_url = os.getenv('SELLER_SERVICE_URL', 'http://default-seller-service-url')

# API Keys

TRACKINGMORE_API_KEY = os.getenv('TRACKINGMORE_API_KEY', 'ti6225pj-2o0k-11tw-l588-w41y04dx9s4l')
SHIPENGINE_API_KEY = os.getenv('SHIPENGINE_API_KEY', 'TEST_X/LLMqUP+3WsYMj37bImpuWcJJzP0koHzPwbbrmodz4')

# Initialize JWT Manager
app.config['JWT_SECRET_KEY'] = 'dbuserdbuser'  
jwt = JWTManager(app)


# Helper function for retrying requests
def make_service_request(url, headers):
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    response = session.get(url, headers=headers)
    return response

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
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

 # Grants decorator
def grants_required(grant):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add logic for verifying grants
            return func(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/seller/login', methods=['POST'])
def login_seller():
    """
    Login a seller
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login successful, returns JWT token
      400:
        description: Invalid email or password
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

@app.route('/customer/<int:customer_id>/orders/<int:order_id>/tracking', methods=['GET'])
@grants_required('view_order')
def get_order_tracking(customer_id, order_id):
    """
    Track an order's shipping status
    ---
    parameters:
      - name: customer_id
        in: path
        required: true
        type: integer
      - name: order_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: Tracking information
      404:
        description: Order or tracking information not found
      500:
        description: Internal server error
    """
    # Retrieve order details from Order Service
    headers = {
        'X-Correlation-ID': g.get('correlation_id', 'default-correlation-id'),
        'Authorization': request.headers.get('Authorization', '')
    }
    order_resp = make_service_request(f'{order_service_url}/orders/{order_id}', headers=headers)
    if order_resp.status_code != 200:
        return jsonify({"error": "Failed to retrieve order details"}), order_resp.status_code

    order_info = order_resp.json()
    tracking_number = order_info.get('tracking_number')
    if not tracking_number:
        return jsonify({"error": "No tracking number available for this order"}), 404

    tm_headers = {
        'Trackingmore-Api-Key': TRACKINGMORE_API_KEY,
        'Content-Type': 'application/json'
    }

    # Attempt to create tracking in TrackingMore
    create_payload = {
        "tracking_number": tracking_number,
        "carrier_code": "ups"
    }
    create_resp = requests.post(
        'https://api.trackingmore.com/v2/trackings/create',
        headers=tm_headers,
        data=json.dumps(create_payload)
    )

    if create_resp.status_code not in [200, 201, 409]:
        return jsonify({"error": "Failed to create tracking", "details": create_resp.text}), create_resp.status_code

    # Retrieve tracking details
    tm_response = make_service_request(
        'https://api.trackingmore.com/v2/trackings/get',
        headers=tm_headers
    )
    if tm_response.status_code == 200:
        tm_data = tm_response.json()
        if 'data' in tm_data and len(tm_data['data']) == 0:
            tracking_link = f"https://www.trackingmore.com/track/en/{tracking_number}?express=ups"
            return jsonify({"link": tracking_link}), 200
        return jsonify(tm_data), 200
    else:
        return jsonify({"error": "Failed to retrieve tracking details", "details": tm_response.text}), tm_response.status_code

@app.route('/seller_management/<int:seller_id>', methods=['GET'])
@grants_required('view_order')
def seller_management(seller_id):
    """
    Retrieve seller dashboard link
    ---
    parameters:
      - name: seller_id
        in: path
        required: true
        type: integer
    responses:
      200:
        description: Seller management dashboard URL
      404:
        description: Seller not found
      500:
        description: Internal server error
    """
    headers = {
        'X-Correlation-ID': g.get('correlation_id', 'default-correlation-id'),
        'Authorization': request.headers.get('Authorization', '')
    }
    seller_resp = make_service_request(f'{seller_service_url}/seller/{seller_id}', headers=headers)
    if seller_resp.status_code != 200:
        return jsonify({"error": "Failed to retrieve seller details"}), seller_resp.status_code

    seller_info = seller_resp.json()
    seller_name = seller_info.get('name', 'Unknown')
    dashboard_url = f"https://dashboard.shipengine.com/?user_id={seller_id}&name={seller_name}"

    return jsonify({"seller_id": seller_id, "dashboard_url": dashboard_url}), 200

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
        in: 
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
