import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


from agent.merchant import A3AMerchantAgent




if __name__ == '__main__':
    A3AMerchantAgent.run()