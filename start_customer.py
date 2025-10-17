import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
from agent.customer import A3ACustomerAgent


if __name__ == '__main__':
    A3ACustomerAgent.run()