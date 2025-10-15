from utils.authlib import auth_login
import requests

ctx = []
TEST_WALLET = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'
TEST_WALLET_PRIVATE_KEY = '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d'

#============== This should be done by frontend =======
auth_res= auth_login(TEST_WALLET_PRIVATE_KEY)
access_token = auth_res['token']
headers = {'Authorization': f'Bearer {access_token}'}

orderId = '1'

# 1. Check the user's wallet has at LEAST 20 A3AToken Allowance AND Balance
resp= requests.post('http://127.0.0.1:5000/api/orders/{orderId}/confirm-payment',json={
    'txHash':'0x0401c7dd85d0da2639da04a5c128ce42d4b0203a367139154526e5952026a108'
}, headers=headers).json()
print('✅ Send /api/confirm-payment Successfully')
print(resp)