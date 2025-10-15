import requests
from utils.authlib import auth_login
from utils.sc_tools import *
import json,os,sys

ctx = []
TEST_WALLET = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'
TEST_WALLET_PRIVATE_KEY = '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d'

#============== This should be done by frontend =======
auth_res= auth_login(TEST_WALLET_PRIVATE_KEY)
access_token = auth_res['token']
headers = {'Authorization': f'Bearer {access_token}'}


# 1. Check the user's wallet has at LEAST 20 A3AToken Allowance AND Balance
resp= requests.post('http://127.0.0.1:5000/api/user/a3atoken/allowance', headers=headers).text
allowance = float(resp)
resp= requests.post('http://127.0.0.1:5000/api/user/a3atoken/balance', headers=headers).text
balance = float(resp)
print(f'🔍 Your A3AToken allowance: {allowance}')
print(f'🔍 Your A3AToken balance: {balance}')

if balance<20:
    print("❌ Fail to do chat! The A3AToken balance is insufficient!")
    sys.exit(-1)
if allowance<20:
    # using ether.js maybe?
    # This include private key signature
    approve_address(TEST_WALLET_PRIVATE_KEY,10000)
#============== =============================== =======


while True:
    prompt = input("input chat message:")
    ctx.append({
    'role':'user',
    'content':prompt})

    resp= requests.post('http://127.0.0.1:5000/api/chat/messages', json={'messages':ctx
    }, headers=headers).json()
    msg_type = resp['type']
    if msg_type == 'chat':
        print('📋 '+resp['content'])
        ctx.append({'role':'assistant','content':resp['content']})

    elif msg_type == 'order':
        print('✅ ')
        print(resp['content'])
