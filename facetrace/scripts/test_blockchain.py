import os
import json
import solcx
from web3 import Web3, EthereumTesterProvider

def main():
    # 1. Install specific solc version if missing
    try:
        solcx.install_solc('0.8.20')
        solcx.set_solc_version('0.8.20')
    except Exception as e:
        print(f"Error setting solc: {e}")

    contract_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "EvidenceRegistry.sol")
    with open(contract_path, "r") as f:
        source = f.read()

    print("Compiling contract...")
    compiled_sol = solcx.compile_source(
        source,
        output_values=["abi", "bin"]
    )
    
    contract_id, contract_interface = compiled_sol.popitem()
    abi = contract_interface['abi']
    bytecode = contract_interface['bin']
    
    # Save abi.json
    abi_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "abi.json")
    with open(abi_path, 'w') as f:
        json.dump(abi, f, indent=4)
        
    print("Connecting to local Eth-Tester provider...")
    w3 = Web3(EthereumTesterProvider())
    w3.eth.default_account = w3.eth.accounts[0]
    
    print(f"Deploying contract from {w3.eth.default_account}...")
    EvidenceRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = EvidenceRegistry.constructor().transact()
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    contract_address = tx_receipt.contractAddress
    print(f"Contract Deployed at: {contract_address}")
    
    # Save deployment info
    dep_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "deployment.json")
    with open(dep_path, 'w') as f:
        json.dump({"address": contract_address}, f, indent=4)

    # Instantiate the contract and run a real transaction
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    test_fingerprint = "cf23df2207d99a74fbe169e3eba035e633b65d94"
    print(f"\nRegistering evidence fingerprint: {test_fingerprint}...")
    
    reg_tx = contract.functions.registerEvidence(test_fingerprint).transact()
    reg_receipt = w3.eth.wait_for_transaction_receipt(reg_tx)
    
    print(f"\nREAL TRANSACTION SUCCESSFUL.")
    print(f"Tx Hash: {reg_tx.hex()}")
    print(f"Gas Used: {reg_receipt.gasUsed}")
    print(f"Block Number: {reg_receipt.blockNumber}")
    
    # Verify the state
    exists, timestamp, registrar = contract.functions.verifyEvidence(test_fingerprint).call()
    print(f"\nVerification Results:")
    print(f"- Exists: {exists}")
    print(f"- Timestamp: {timestamp}")
    print(f"- Registrar: {registrar}")

if __name__ == "__main__":
    main()
