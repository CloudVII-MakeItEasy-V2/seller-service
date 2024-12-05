# product.py
from db_setup import db

class Product(db.Model):
    __tablename__ = 'Product'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('Seller.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200))
    category = db.Column(db.String(100))

    def update_stock(self, quantity):
        self.stock += quantity

    def get_details(self):
        return {
            'product_id': self.id,
            'name': self.name,
            'price': self.price,
            'stock': self.stock,
            'description': self.description,
            'category': self.category
        }

    def check_availability(self, required_quantity):
        return self.stock >= required_quantity