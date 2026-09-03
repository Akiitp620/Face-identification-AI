# FaceTrace
## Evidence Discovery & Blockchain Verification

FaceTrace is an evidence-discovery and provenance system that combines local facial feature extraction, genuine web visual search, candidate similarity ranking, deterministic SHA-256 fingerprinting, and Ethereum Sepolia verification into a single investigation workflow.

> **AI finds the evidence. Cryptography fingerprints it. Blockchain preserves the proof.**

---

## 1. Problem

Digital evidence discovered online can be difficult to preserve and verify reliably. Images may be edited, URLs may disappear, and the same evidence may be encountered in multiple forms across the web.

FaceTrace addresses this provenance problem by creating a reproducible workflow for discovering visual evidence, selecting a candidate based on local face similarity, generating a deterministic cryptographic fingerprint, and registering that fingerprint on a blockchain.

The system is designed to verify the **integrity and provenance of a captured evidence record**, not to establish the absolute truth or identity represented by an image.

---

## 2. Solution

FaceTrace provides an end-to-end evidence discovery and verification pipeline:

- Detect and encode a face locally using PyTorch.
- Perform genuine visual web discovery through Google Lens via SerpApi.
- Retrieve and rank discovered candidates using local facial embeddings.
- Select the highest-ranked valid candidate as canonical evidence.
- Generate a deterministic SHA-256 fingerprint of the canonical evidence record.
- Optionally preserve discovered evidence binaries through IPFS.
- Register the fingerprint on an Ethereum Sepolia smart contract.
- Re-compute and compare the fingerprint against the on-chain record.
- Demonstrate tamper detection by intentionally modifying the canonical evidence record.

The resulting workflow provides a verifiable record that can be independently checked against the blockchain registration.

---

## 3. How It Works

FaceTrace follows a strict sequential workflow:

### 1. Face Scan

The system detects a face using **MTCNN** and extracts a **512-dimensional facial embedding** using `InceptionResnetV1` from `facenet-pytorch`.

Face processing runs locally rather than relying on a third-party facial recognition API.

### 2. Genuine Web Discovery

The target image is submitted to **Google Lens through SerpApi** for genuine visual web discovery.

Results are dynamically obtained from the external API. No pre-selected or hardcoded final matching result is used.

### 3. Candidate Ranking

Discovered candidate images are fetched and processed locally.

Each valid candidate is encoded and compared against the target face embedding using cosine similarity. Candidates are then ranked according to their visual facial similarity.

### 4. Evidence Selection

The highest-ranked valid candidate is selected as the canonical evidence record.

The evidence record contains the relevant discovered metadata, source information, and optional storage reference.

### 5. SHA-256 Fingerprinting

A deterministic SHA-256 fingerprint is generated from the canonical evidence representation.

The same evidence metadata, source URL, and optional IPFS CID produce the same fingerprint, enabling reproducible verification.

### 6. Sepolia Blockchain Registration

The resulting fingerprint is converted to a `bytes32` value and registered through the deployed `EvidenceRegistry.sol` smart contract on the **Ethereum Sepolia Testnet**.

The transaction creates a public blockchain-backed record containing the fingerprint, registrar, and registration timestamp.

### 7. On-chain Verification

During verification, FaceTrace re-computes the fingerprint from the active evidence record and queries the Sepolia smart contract.

If the fingerprint exists on-chain, the system reports the associated registration information.

### 8. Tamper Detection

The system can deliberately modify the canonical evidence record and re-compute its fingerprint.

Because SHA-256 is deterministic, even a small change produces a different fingerprint. The altered record therefore fails the on-chain lookup and is reported as a verification mismatch.

---

## 4. Architecture

FaceTrace separates the user interface from the core processing engines.

```text
                         ┌─────────────────────┐
                         │   Streamlit Console  │
                         │       app.py        │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
          │ Face Engine  │  │  Discovery   │  │   Ranking    │
          │ PyTorch      │  │ SerpApi      │  │ Face Similarity│
          └──────────────┘  └──────────────┘  └──────────────┘
                  │                 │                 │
                  └─────────────────┼─────────────────┘
                                    ▼
                           ┌─────────────────┐
                           │ Canonical       │
                           │ Evidence Record │
                           └────────┬────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
                    ▼               ▼                ▼
              ┌──────────┐   ┌─────────────┐  ┌─────────────┐
              │ SHA-256  │   │ Optional    │  │   Source    │
              │ Fingerprint│ │ IPFS/Pinata │  │   Metadata  │
              └─────┬────┘   └─────────────┘  └─────────────┘
                    │
                    ▼
             ┌──────────────────┐
             │ EvidenceRegistry │
             │ Ethereum Sepolia │
             └────────┬─────────┘
                      │
                      ▼
             ┌──────────────────┐
             │ Re-verification  │
             │ + Tamper Check   │
             └──────────────────┘
