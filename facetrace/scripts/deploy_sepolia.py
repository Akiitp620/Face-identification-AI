import os
import sys
import json
import solcx
from web3 import Web3
from dotenv import load_dotenv

def main():
    # Load environment variables
    # Specify dotenv_path to ensure it loads from facetrace/.env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path=env_path)

    rpc_url = os.getenv("RPC_URL")
    private_key = os.getenv("BLOCKCHAIN_PRIVATE_KEY")

    if not rpc_url:
        print("ERROR: RPC_URL missing from .env")
        sys.exit(1)
    
    if not private_key:
        print("ERROR: BLOCKCHAIN_PRIVATE_KEY missing from .env")
        sys.exit(1)

    print("Connecting to Sepolia RPC...")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("ERROR: Failed to connect to RPC_URL")
        sys.exit(1)

    chain_id = w3.eth.chain_id
    print(f"Connected to Chain ID: {chain_id}")
    
    if chain_id != 11155111:
        print(f"ERROR: Expected Chain ID 11155111 (Sepolia), got {chain_id}")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    deployer_address = account.address
    print(f"Deployer Address: {deployer_address}")

    # Check balance
    balance_wei = w3.eth.get_balance(deployer_address)
    balance_eth = w3.from_wei(balance_wei, 'ether')
    print(f"Deployer Balance: {balance_eth} ETH")

    if balance_wei == 0:
        print("ERROR: Deployer account has 0 Sepolia ETH. Cannot deploy.")
        sys.exit(1)

    # Compile contract
    print("Installing/Setting solc 0.8.20...")
    try:
        solcx.install_solc('0.8.20')
        solcx.set_solc_version('0.8.20')
    except Exception as e:
        print(f"ERROR: Failed to setup solc: {e}")
        sys.exit(1)

    contract_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "EvidenceRegistry.sol")
    print(f"Compiling {contract_path}...")
    with open(contract_path, "r") as f:
        source = f.read()

    compiled_sol = solcx.compile_source(
        source,
        output_values=["abi", "bin"]
    )

    contract_id, contract_interface = compiled_sol.popitem()
    abi = contract_interface['abi']
    bytecode = contract_interface['bin']

    # Build deployment transaction
    print("Building deployment transaction...")
    EvidenceRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Get current nonce and gas price
    nonce = w3.eth.get_transaction_count(deployer_address)
    
    # Build constructor tx
    construct_txn = EvidenceRegistry.constructor().build_transaction({
        'chainId': chain_id,
        'gas': 3000000, # Fallback, will estimate below if possible
        'maxFeePerGas': w3.eth.gas_price * 2,
        'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
        'nonce': nonce,
    })

    try:
        # Estimate gas properly
        estimated_gas = w3.eth.estimate_gas(construct_txn)
        construct_txn['gas'] = int(estimated_gas * 1.2) # Add 20% buffer
    except Exception as e:
        print(f"Gas estimation failed, using fallback: {e}")

    # Sign transaction
    print("Signing deployment transaction...")
    signed_txn = w3.eth.account.sign_transaction(construct_txn, private_key=private_key)

    # Broadcast transaction
    print("Broadcasting transaction to Sepolia...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Deployment Transaction Hash: {tx_hash.hex()}")

    # Wait for receipt
    print("Waiting for transaction receipt...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if tx_receipt.status != 1:
        print("ERROR: Deployment transaction failed (status 0).")
        sys.exit(1)

    contract_address = tx_receipt.contractAddress
    print(f"\n✅ SUCCESSFULLY DEPLOYED TO SEPOLIA")
    print(f"Contract Address: {contract_address}")
    print(f"Chain ID: {chain_id}")

    # Save ABI
    abi_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "abi.json")
    with open(abi_path, 'w') as f:
        json.dump(abi, f, indent=4)
    print(f"Saved ABI to {abi_path}")

    # Save Deployment Info
    dep_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "deployment.json")
    with open(dep_path, 'w') as f:
        json.dump({"address": contract_address}, f, indent=4)
    print(f"Saved deployment address to {dep_path}")

    # Sanity Check (Read/Write)
    print("\n--- Running Sanity Check ---")
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    dummy_fingerprint = "cf23df2207d99a74fbe169e3eba035e633b65d94cf23df2207d99a74fbe169e3"
    print(f"Registering dummy fingerprint: {dummy_fingerprint}")
    
    # Needs 0x prefix or 32 bytes
    try:
        bytes32_fingerprint = Web3.to_bytes(hexstr=dummy_fingerprint)
        
        sanity_nonce = w3.eth.get_transaction_count(deployer_address)
        reg_txn = contract.functions.registerEvidence(bytes32_fingerprint).build_transaction({
            'chainId': chain_id,
            'maxFeePerGas': w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
            'nonce': sanity_nonce,
        })
        
        # Estimate gas for function call
        reg_gas = w3.eth.estimate_gas(reg_txn)
        reg_txn['gas'] = int(reg_gas * 1.2)
        
        signed_reg_txn = w3.eth.account.sign_transaction(reg_txn, private_key=private_key)
        reg_tx_hash = w3.eth.send_raw_transaction(signed_reg_txn.raw_transaction)
        print(f"Registration Tx Hash: {reg_tx_hash.hex()}")
        
        reg_receipt = w3.eth.wait_for_transaction_receipt(reg_tx_hash)
        
        if reg_receipt.status == 1:
            print("Write test: PASS")
            
            # Read test
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
