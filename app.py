from flask import Flask

from api.auth import auth_bp
from api.customer import customer_bp
from api.merchant import merchant_bp
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "aayotyrelqy8174udah"
jwt = JWTManager(app)
app.register_blueprint(auth_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(merchant_bp)

@app.route("/")
def index():
    return "Welcome to the Fiducia API!"

if __name__ == '__main__':
    
    app.run(debug=True, port=5000)