import requests
from utils.authlib import auth_login
import json
auth_res= auth_login()
access_token = auth_res['token']
headers = {'Authorization': f'Bearer {access_token}'}
ctx = []
while True:
    prompt = input("input prompt:")
    ctx.append({
    'role':'user',
    'content':prompt})

    resp= requests.post('http://127.0.0.1:5000/api/chat/messages', json={'messages':ctx
    }, headers=headers) 
    print(resp.json()['content'])
    ctx.append({'role':'assistant','content':resp.json()['content']})
