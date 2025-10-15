## Backend endpoints
### currently implemented:
1. /api/auth/challenge
2. /api/auth/login
3. /api/chat/messages (only chat part, order is not implemented)

### Smart Contract startup:
1. git clone -b feature/backend-integration-test git@github.com:Fiducia-ETHOnline/smart-contract-for-orderAgent.git  
2. cd to the directory  
3. forge build  
4. run:  
```
anvil
```
5. Then, run:  
```
forge script script/DeployOrderContract.s.sol:DeployOrderContract --rpc-url 127.0.0.1:8545 --broadcast --private-key 0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba
```  
You should see sth like this:  
```
== Return ==
0: contract OrderContract 0x5FbDB2315678afecb367f032d93F642f64180aa3
1: contract HelperConfig 0xC7f2Cf4845C6db0e1a1e91ED41Bcd0FcC1b0E141

== Logs ==
  pyUSD deployed at: 0x0116686E2291dbd5e317F47faDBFb43B599786Ef
```  
### Start Backend:
1. run:
```
python app.py
```
### Start Agents:

2. run:  
```
python start_customer.py
python start_merchant.py
```

### Test:
1. chatbot:  
```
python test/chat.py 
```

2. get_order:
```
python test/get_orders.py 
```