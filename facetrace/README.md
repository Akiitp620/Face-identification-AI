# FaceTrace
## Evidence Discovery & Blockchain Verification

---

### 1. Problem
In the era of deepfakes, AI-generated imagery, and ephemeral digital content, verifying the origin and authenticity of OSINT (Open Source Intelligence) findings is increasingly difficult. Digital evidence found online today can easily be altered, silently edited, or deleted tomorrow, breaking the chain of custody.

### 2. Solution
FaceTrace provides an end-to-end, cryptographically verifiable pipeline to establish a permanent chain of custody for digital evidence. It allows investigators to discover visual evidence online, rank it via local biometric AI, preserve the raw binaries decentrally, and anchor cryptographic proofs onto a blockchain ledger.

### 3. How It Works
The system follows a strict, sequential core workflow:
1. **Face Scan**: Extracts a robust 512-dimensional facial embedding using a local PyTorch model.
2. **Genuine Google Lens / SerpApi Discovery**: Searches the web for visually similar instances using Google Lens via SerpApi.
3. **Candidate Ranking**: Fetches candidate images and ranks them biometrically against the target subject.
4. **Evidence Selection**: Selects the highest-ranked candidate as canonical evidence.
5. **SHA-256 Fingerprint**: Generates a deterministic hash of the evidence metadata, source URL, and IPFS CID.
6. **Sepolia Blockchain Registration**: Commits the fingerprint to an EVM smart contract (`EvidenceRegistry.sol`).
7. **On-chain Verification**: Reads the fingerprint back from the blockchain to verify timestamp and registrar provenance.
8. **Tamper Detection**: Demonstrates cryptographic fragility; any alteration to the binary or metadata results in a mismatch.

### 4. Architecture
FaceTrace separates the UI from the heavy backend engines:
- **`app.py`**: The Streamlit user interface and workflow orchestrator.
- **`core/`**: Independent Python modules handling the Face Engine (PyTorch), Discovery (SerpApi), Ranking, Fingerprinting, IPFS pinning, and Web3 interactions.
- **`blockchain/`**: The Solidity smart contract layer (`EvidenceRegistry.sol`) defining the immutable ledger rules.
- **`tests/`**: An isolated suite of `pytest` unit tests for core engine components.

### 5. Key Features
- **Local Biometric Verification**: Prevents reliance on opaque, third-party closed-source facial recognition APIs by executing FaceNet locally.
- **Decentralized Preservation**: Optionally pins the raw binary of the discovered evidence to the InterPlanetary File System (IPFS) via Pinata, preventing dead links (when API credentials are provided).
- **Cryptographic Anchoring**: Logs a `bytes32` hash on the Ethereum Sepolia Testnet, securing a permanent, public timestamp.
- **Deterministic Hashing**: Ensures that the exact combination of Context, Source URL, and Binary CID produces an identical, repeatable fingerprint.

### 6. Technology Stack
- **Frontend / Console**: Streamlit
- **AI / Biometrics**: PyTorch, `facenet-pytorch` (MTCNN + InceptionResnetV1)
- **OSINT Discovery**: SerpApi (Google Lens API)
- **Decentralized Storage**: IPFS (Pinata SDK/API)
- **Blockchain / Web3**: Solidity, `web3.py`, Sepolia Testnet
- **Testing**: `pytest`, `unittest.mock`

### 7. Blockchain Verification
During the verification stage, the console re-computes the SHA-256 fingerprint from the active evidence object and queries the Sepolia blockchain. If the fingerprint exists in the `EvidenceRegistry` contract, the UI surfaces the exact wallet address of the registrar and the block timestamp, proving the evidence existed at that point in time.

### 8. Tamper Detection
FaceTrace simulates a tamper scenario by deliberately modifying a single character in the IPFS CID of the canonical evidence. Because the fingerprinting algorithm is deterministic, this microscopic change completely alters the resulting SHA-256 hash. When queried against the blockchain, the verification engine correctly rejects the tampered evidence as unregistered.

### 9. Responsible Use / Limitations
- **Intended Audience**: OSINT researchers, journalists, and legal professionals.
- **Restrictions**: Must not be used for unauthorized surveillance, doxxing, or violating privacy terms of service.
- **Technical Limits**: Web-discovery target images are limited to **500 KB** to optimize SerpApi processing. IPFS pinning is restricted to candidates under **5 MB**. The candidate ranking engine processes candidates asynchronously but enforces strict timeouts.

### 10. Project Structure
```text
facetrace/
├── app.py                      # Main Streamlit investigation console
├── core/
│   ├── blockchain.py           # Web3 integration
│   ├── candidate_ranker.py     # Biometric matching
│   ├── discovery.py            # SerpApi integration
│   ├── evidence.py             # Canonical evidence data structures
│   ├── face_engine.py          # PyTorch MTCNN/InceptionResnet
│   ├── fingerprint.py          # Deterministic SHA-256 hashing
│   ├── ipfs.py                 # Pinata IPFS pinning
│   └── verifier.py             # On-chain verification logic
├── blockchain/
│   ├── EvidenceRegistry.sol    # The EVM smart contract
│   ├── abi.json                # Compiled contract ABI
│   └── deployment.json         # Deployed contract address
├── scripts/
│   └── deploy_sepolia.py       # Contract deployment script
├── tests/                      # Formal pytest suite
├── utils/
│   └── config.py               # Environment configuration
└── requirements.txt            # Python dependencies
```

### 11. Setup
1. **Clone the repository:**
   ```bash
   git clone <repo_url>
   cd facetrace
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 12. Environment Variables
Create a `.env` file in the root directory:
```env
# OSINT Discovery
SERPAPI_API_KEY="<YOUR_SERPAPI_KEY>"

# Web3 / Blockchain
RPC_URL="<YOUR_SEPOLIA_RPC_URL>"
BLOCKCHAIN_PRIVATE_KEY="<YOUR_WALLET_PRIVATE_KEY>"
CONTRACT_ADDRESS="0x1aE23E929958Ef7f807D4852204C3279c86dE67b"

# Decentralized Storage (IPFS)
PINATA_API_KEY="<YOUR_PINATA_API_KEY>"
PINATA_SECRET_API_KEY="<YOUR_PINATA_SECRET_API_KEY>"
```

### 13. Running the Application
To start the FaceTrace investigation console, run:
```bash
streamlit run app.py
```

### 14. Demo
1. Ensure your `.env` is fully populated.
2. Run the application and open the Streamlit web interface.
3. Upload a target face image (under 500 KB).
4. Click **Run OSINT Discovery Workflow**.
5. Once evidence is generated, click **Commit to Distributed Ledger** to anchor the cryptographic proof.

### 15. Test Results
The repository includes a formal test suite covering the core AI, logic, and blockchain integration components.
- **Framework**: `pytest`
- **Total Tests**: 18
- **Status**: 100% Pass Rate
- **Coverage**: Includes unit tests for the PyTorch face engine, SerpApi discovery error handling, biometric ranking math, deterministic SHA-256 fingerprinting, and EVM verification states. No unhandled async warnings.
