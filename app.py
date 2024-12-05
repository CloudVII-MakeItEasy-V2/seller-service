from flask import Flask, request, jsonify
from flasgger import Swagger  # For OpenAPI documentation
from db_setup import db
from seller import Seller
from product import Product

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://yj2747:dbuserdbuser@makeiteasy.ck0scewemjwp.us-east-1.rds.amazonaws.com:3306/Seller_Service'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
Swagger(app)  # Initialize Swagger

@app.route('/')
def index():
    return 'Welcome to the Seller Service API!'

@app.route('/test-db-connection', methods=['GET'])
def test_db_connection():
    """Test the database connection
    ---
    responses:
      200:
        description: Database connected successfully
      500:
        description: Database connection error
    """
    try:
        sellers = Seller.query.all()
        return jsonify({"message": "Database connection successful", "sellers": len(sellers)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/seller/register', methods=['POST'])
def register_seller():
    """Register a new seller
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
    responses:
      201:
        description: Seller created successfully
      400:
        description: Invalid input
    """
    data = request.json
    name = data.get('name')
    email = data.get('email')

    new_seller = Seller(name=name, email=email)
    db.session.add(new_seller)
    db.session.commit()

    return jsonify({
        "seller": new_seller.register_seller(),
        "links": [
            {"rel": "self", "href": f"/seller/{new_seller.id}"},
            {"rel": "products", "href": f"/seller/{new_seller.id}/products"}
        ]
    }), 201

@app.route('/product', methods=['POST'])
def create_product():
    """Create a new product
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
              type: float
            stock:
              type: integer
            description:
              type: string
            category:
              type: string
    responses:
      201:
        description: Product created successfully
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

    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({"error": "Seller not found"}), 404

    new_product = Product(seller_id=seller.id, name=name, price=price, stock=stock, description=description, category=category)
    db.session.add(new_product)
    db.session.commit()

    return jsonify({
        "message": "Product created successfully.",
        "product_id": new_product.id,
        "links": [
            {"rel": "self", "href": f"/product/{new_product.id}"},
            {"rel": "seller", "href": f"/seller/{seller_id}"}
        ]
    }), 201

# Main entry point
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000, debug=True)