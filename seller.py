# seller.py
from db_setup import db

class Seller(db.Model):
    __tablename__ = 'Seller'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

    products = db.relationship('Product', backref='seller', lazy=True)

    def register_seller(self):
        return {"id": self.id, "name": self.name, "email": self.email}