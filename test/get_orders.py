from utils.authlib import auth_login
import requests

ctx = []
TEST_WALLET = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'
TEST_WALLET_PRIVATE_KEY = '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d'

#============== This should be done by frontend =======
auth_res= auth_login(TEST_WALLET_PRIVATE_KEY)
access_token = auth_res['token']
headers = {'Authorization': f'Bearer {access_token}'}


# 1. Check the user's wallet has at LEAST 20 A3AToken Allowance AND Balance
resp= requests.get('http://127.0.0.1:5000/api/orders', headers=headers).json()
print('✅ Send /api/orders Successfully')
print(resp)