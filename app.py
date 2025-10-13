from flask import Flask

from api.auth import auth_bp
from api.customer import customer_bp
from api.merchant import merchant_bp


app = Flask(__name__)


app.register_blueprint(auth_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(merchant_bp)

@app.route("/")
def index():
    return "Welcome to the Fiducia API!"

if __name__ == '__main__':
    
    app.run(debug=True, port=5000)