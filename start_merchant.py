import os
os.environ['CONTRACT_URL'] = 'http://127.0.0.1:8545'
os.environ['AGENT_CONTRACT'] = '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512'
os.environ['PYUSD_ADDRESS'] = '0x0116686E2291dbd5e317F47faDBFb43B599786Ef'
# os.environ['AGENT_PRIVATE_KEY']='0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba'


from agent.merchant import A3AMerchantAgent




if __name__ == '__main__':
    A3AMerchantAgent.run()