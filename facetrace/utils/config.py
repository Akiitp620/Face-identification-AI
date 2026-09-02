import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
    PINATA_API_KEY = os.getenv("PINATA_API_KEY")
    PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY")
    RPC_URL = os.getenv("RPC_URL")
    BLOCKCHAIN_PRIVATE_KEY = os.getenv("BLOCKCHAIN_PRIVATE_KEY")
    CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
    CHAIN_ID = os.getenv("CHAIN_ID")
