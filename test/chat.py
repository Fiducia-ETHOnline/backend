import requests
from utils.authlib import auth_login
import json
auth_res= auth_login()
access_token = auth_res['token']
headers = {'Authorization': f'Bearer {access_token}'}
with requests.post('http://127.0.0.1:5000/api/chat/messages', json={'messages':[{
    'role':'user',
    'content':'who are you?'}]
}, headers=headers,stream=True) as resp:
    print("Start stream post")
    for line in resp.iter_lines():
        if line:
            try:
                data = json.loads(line.decode("utf-8"))
                print(data.get("content", ""), end="", flush=True)
            except Exception:
                print(line.decode("utf-8"))

