import os
import sys
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.config import Config
print(Config.RPC_URL)
from web3 import Web3
w3 = Web3(Web3.HTTPProvider(Config.RPC_URL))
print(w3.is_connected())
