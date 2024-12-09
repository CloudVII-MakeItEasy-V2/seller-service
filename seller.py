from db_setup import db

class Seller(db.Model):
    __tablename__ = 'Seller'

    seller_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # Must not be null
    balance = db.Column(db.Integer, nullable=False, default=0)  # Added balance with default 0

    products = db.relationship('Product', backref='seller', lazy=True)

    def register_seller(self):
        return {
            "id": self.seller_id,
            "name": self.name,
            "email": self.email,
            "balance": self.balance  # Include balance in response
        }

    def get_details(self):
        return {
            "seller_id": self.seller_id,
            "name": self.name,
            "email": self.email,
            "balance": self.balance  # Include balance in response
        }

    def update_balance(self, amount):
        self.balance += amount