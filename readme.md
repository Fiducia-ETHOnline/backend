## Backend endpoints
### currently implemented:
1. /api/auth/challenge
2. /api/auth/login
3. /api/chat/messages (only chat part, order is not implemented)

### Tests:
1. run:
```
python app.py
python test/auth.py 
```
to test auth process  
2. run:
```
python agent/customer.py
python app.py
python test/chat.py 
```
To test /api/chat/message endpoint