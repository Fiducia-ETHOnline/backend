from functools import wraps
from flask import request, jsonify


def get_user_from_token(token):

    if token == "fake_business_jwt_token":
        return {"address": "0x22222...", "role": "business"}

    elif token and token.startswith("fake_"):
        return {"address": "0x11111...", "role": "customer"}
    return None

def token_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(" ")[1]

            if not token:
                return jsonify({"message": "Token is missing!"}), 401

            
            user = get_user_from_token(token)

            if not user:
                return jsonify({"message": "Token is invalid!"}), 401

            
            if role and user.get("role") != role:
                return jsonify({"message": f"Insufficient permissions! Requires role: {role}"}), 403

            
            return f(*args, **kwargs)
        return decorated_function
    return decorator