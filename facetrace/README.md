# FaceTrace

> OSINT discovers the evidence. PyTorch analyzes it. IPFS and Blockchain preserve the proof.

## Overview
FaceTrace is an AI-powered evidence provenance system. It discovers potential evidence based on a target subject's face using Bing Visual Search, ranks candidates biometrically using a local PyTorch FaceNet model, pins the raw evidence binaries to IPFS, and anchors cryptographic fingerprints on an EVM-compatible blockchain.

## Problem
In the era of deepfakes and ephemeral digital content, verifying the origin and authenticity of OSINT (Open Source Intelligence) findings is increasingly difficult. Evidence found online today might be altered or deleted tomorrow.

## Solution
FaceTrace provides an end-to-end, cryptographically verifiable pipeline:
1. **Discover:** Find relevant images across the web using robust search indices.
2. **Analyze:** Verify biometric similarity locally, without relying on opaque third-party AI APIs.
3. **Preserve:** Anchor the exact state of the digital evidence into a decentralized storage network (IPFS).
4. **Prove:** Register a unique, unforgeable hash of the evidence metadata and IPFS CID to a blockchain ledger.

## Architecture

### Technology Stack
- **Frontend**: Streamlit
- **AI/Biometrics**: PyTorch, Facenet-PyTorch (MTCNN + InceptionResnetV1)
- **OSINT Discovery**: Bing Visual Search API
- **Decentralized Storage**: IPFS (via Pinata)
- **Ledger/Provenance**: Web3.py, Solidity (EVM)

### Workflow
1. **Face Identification**: A target image is uploaded. The local PyTorch model extracts a robust 512-dimensional facial embedding.
2. **Genuine Web Discovery**: The image is sent to Bing Visual Search to discover visually similar instances across the web.
3. **Candidate Matching**: All discovered candidate images are fetched asynchronously. The local PyTorch model compares their embeddings against the target, assigning a similarity score.
4. **Evidence Preservation**: The highest-ranked candidate's raw binary is uploaded and pinned to IPFS, generating a permanent CID.
5. **Evidence Fingerprinting**: A deterministic JSON structure (containing the source URL, IPFS CID, and context metadata) is hashed via SHA-256.
6. **Blockchain Verification**: The SHA-256 fingerprint is registered as a `bytes32` hash on an EVM smart contract, logging the exact timestamp and registrar address.

## Security & Tamper Detection
Any alteration to the underlying IPFS binary or the context metadata will completely change the deterministic SHA-256 hash. FaceTrace's verification engine can detect these discrepancies instantly by comparing the re-calculated hash against the on-chain registry, ensuring deepfakes or altered records are immediately flagged.

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repo_url>
   cd facetrace
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   # Web3 Configuration
   WEB3_RPC_URL="<YOUR_RPC_URL>"
   PRIVATE_KEY="<YOUR_PRIVATE_KEY>"
   CONTRACT_ADDRESS="<DEPLOYED_CONTRACT_ADDRESS>"
   
   # Bing Visual Search
   BING_API_KEY="<YOUR_BING_API_KEY>"
   
   # Pinata (IPFS)
   PINATA_API_KEY="<YOUR_PINATA_API_KEY>"
   PINATA_API_SECRET="<YOUR_PINATA_API_SECRET>"
   ```

## Running Locally

To start the console:
```bash
streamlit run app.py
```

## Known Limitations
- The system currently processes up to 10 candidates concurrently to manage memory limits and prevent blocking the main thread during heavy image processing.
- IPFS uploads are restricted to images under 5MB to optimize performance during the discovery phase.

## Responsible Use
This tool is intended for OSINT researchers, journalists, and legal professionals. It must not be used for unauthorized surveillance, doxxing, or any activities violating privacy laws and terms of service.
