import os
import sys
import json
from web3 import Web3
from dotenv import load_dotenv

def main():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path=env_path)

    rpc_url = os.getenv("RPC_URL")
    private_key = os.getenv("BLOCKCHAIN_PRIVATE_KEY")
    contract_address = "0x1aE23E929958Ef7f807D4852204C3279c86dE67b"

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("ERROR: Failed to connect to RPC_URL")
        sys.exit(1)

    chain_id = w3.eth.chain_id
    account = w3.eth.account.from_key(private_key)
    deployer_address = account.address

    abi_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "abi.json")
    with open(abi_path, 'r') as f:
        abi = json.load(f)

    print("\n--- Running Sanity Check ---")
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    dummy_fingerprint = "0000000000000000000000000000000000000000000000000000000000000002"
    print(f"Registering dummy fingerprint: {dummy_fingerprint}")
    
    try:
        bytes32_fingerprint = Web3.to_bytes(hexstr=dummy_fingerprint)
        
        sanity_nonce = w3.eth.get_transaction_count(deployer_address)
        reg_txn = contract.functions.registerEvidence(bytes32_fingerprint).build_transaction({
            'chainId': chain_id,
            'maxFeePerGas': w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
            'nonce': sanity_nonce,
        })
        
        reg_gas = w3.eth.estimate_gas(reg_txn)
        reg_txn['gas'] = 300000
        
        signed_reg_txn = w3.eth.account.sign_transaction(reg_txn, private_key=private_key)
        reg_tx_hash = w3.eth.send_raw_transaction(signed_reg_txn.raw_transaction)
        print(f"Registration Tx Hash: {reg_tx_hash.hex()}")
        
        reg_receipt = w3.eth.wait_for_transaction_receipt(reg_tx_hash)
        
        if reg_receipt.status == 1:
            print("Write test: PASS")
            
            exists, timestamp, registrar = contract.functions.verifyEvidence(bytes32_fingerprint).call()
            if exists:
                print("Read test: PASS")
                print(f"Confirmed dummy evidence registered by {registrar} at {timestamp}")
            else:
                print("Read test: FAIL - Evidence not found after successful tx")
        else:
            print("Write test: FAIL - Tx reverted")
            
    except Exception as e:
        print(f"Sanity check failed: {e}")

if __name__ == "__main__":
    main()
