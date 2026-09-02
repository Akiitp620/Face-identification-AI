"""
Responsible ONLY for blockchain interaction.
"""

import os
import json
import logging
from web3 import Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder
from utils.config import Config

logger = logging.getLogger(__name__)

class BlockchainRegistry:
    def __init__(self, w3_provider=None):
        self.rpc_url = Config.RPC_URL
        self.private_key = Config.BLOCKCHAIN_PRIVATE_KEY
        self.contract_address = Config.CONTRACT_ADDRESS
        
        # Use injected provider for testing, or standard HTTP provider
        if w3_provider:
            self.w3 = Web3(w3_provider)
        elif self.rpc_url:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        else:
            self.w3 = None
            logger.warning("RPC_URL is not set. Blockchain integration disabled.")
            return

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Web3 provider")
            
        # load ABI
        abi_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "abi.json")
        if os.path.exists(abi_path):
            with open(abi_path, 'r') as f:
                self.abi = json.load(f)
                
            if self.contract_address:
                self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
        else:
            self.abi = None
            self.contract = None

        # Setup account for manual transactions
        account = self.w3.eth.account.from_key(self.private_key)
        self.account = account

    def register_evidence(self, fingerprint: str) -> str:
        if not self.w3:
            raise ValueError("Blockchain not configured (missing RPC_URL).")
        if not self.private_key or not self.contract_address:
            raise ValueError("BLOCKCHAIN_PRIVATE_KEY or CONTRACT_ADDRESS is missing")
            
        bytes32_fingerprint = Web3.to_bytes(hexstr=fingerprint)
        
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        txn = self.contract.functions.registerEvidence(bytes32_fingerprint).build_transaction({
            'chainId': self.w3.eth.chain_id,
            'maxFeePerGas': self.w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            'nonce': nonce,
        })
        
        estimated_gas = self.w3.eth.estimate_gas(txn)
        txn['gas'] = int(estimated_gas * 1.5) # generous buffer
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            raise Exception("Blockchain transaction failed/reverted")
            
        return tx_hash.hex()

    def verify_evidence(self, fingerprint: str) -> dict:
        if not self.w3:
            raise ValueError("Blockchain not configured.")
        if not self.contract_address:
            raise ValueError("CONTRACT_ADDRESS is missing")
            
        bytes32_fingerprint = Web3.to_bytes(hexstr=fingerprint)
        exists, timestamp, registrar = self.contract.functions.verifyEvidence(bytes32_fingerprint).call()
        return {
            "exists": exists,
            "timestamp": timestamp,
            "registrar": registrar
        }
