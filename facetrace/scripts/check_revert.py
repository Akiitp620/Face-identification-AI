import os
import sys
import json
from web3 import Web3
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)
rpc_url = os.getenv("RPC_URL")

w3 = Web3(Web3.HTTPProvider(rpc_url))
tx_hash = "0x4dd51ffe9064683b882781274cad4847c7e830777db4da1f39568edde0ce8d05"
tx = w3.eth.get_transaction(tx_hash)
print("Gas limit on tx:", tx['gas'])
