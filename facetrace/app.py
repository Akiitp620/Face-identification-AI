import streamlit as st
import copy
from PIL import Image, UnidentifiedImageError
import requests
import graphviz
import logging
from requests.exceptions import RequestException

from core.face_engine import FaceEngine
from core.discovery import DiscoveryEngine
from core.candidate_ranker import CandidateRanker
from core.evidence import Evidence
from core.fingerprint import EvidenceFingerprinter
from core.blockchain import BlockchainRegistry
from core.verifier import EvidenceVerifier
from core.ipfs import IPFSClient
from utils.config import Config

# ==========================================
# CONFIG & STYLING
# ==========================================
st.set_page_config(page_title="FaceTrace Investigation Console", page_icon="🕵️", layout="wide")

st.markdown("""
<style>
    .main-header {
        font-family: 'Courier New', Courier, monospace;
        color: #00FF41;
        border-bottom: 1px solid #00FF41;
        padding-bottom: 10px;
    }
    .console-text {
        font-family: 'Courier New', Courier, monospace;
    }
    div[data-testid="stSidebar"] {
        background-color: #111;
        border-right: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">FaceTrace: Evidence Discovery & Verification Console</h1>', unsafe_allow_html=True)
st.caption("Leverages Bing Visual Search for OSINT discovery, then uses a custom PyTorch FaceNet pipeline to biometrically rank and cryptographically verify the findings on-chain.")

@st.cache_resource
def get_face_engine():
    return FaceEngine()

def init_state():
    for key in ["stage", "candidates", "best_evidence", "canonical_evidence", "fingerprint", "tx_hash", "ranked"]:
        if key not in st.session_state:
            st.session_state[key] = None
    if st.session_state.stage is None:
        st.session_state.stage = 0

init_state()
engine = get_face_engine()

# ==========================================
# 1. FACE INPUT
# ==========================================
st.sidebar.header("1. Face Input")
uploaded_file = st.sidebar.file_uploader("Upload Target Subject Image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.sidebar.image(image, caption="Subject Acquired", use_container_width=True)
    
    # Validation for OSINT Discovery
    discovery_enabled = bool(Config.SERPAPI_API_KEY)
    if not discovery_enabled:
        st.sidebar.warning("OSINT discovery unavailable. Configure SERPAPI_API_KEY in .env.")
        
    if st.sidebar.button("Run OSINT Discovery Workflow", type="primary", disabled=not discovery_enabled):
        with st.spinner("Extracting face embedding..."):
            try:
                embedding = engine.process_face(image)
                st.session_state.embedding = embedding
            except ValueError as e:
                st.sidebar.error(f"Error: {e}")
                st.stop()
            
        with st.spinner("Executing Discovery..."):
            try:
                discovery = DiscoveryEngine()
                uploaded_file.seek(0)
                candidates = discovery.search(uploaded_file.read())
                st.session_state.candidates = candidates
            except Exception as e:
                st.sidebar.error(f"Discovery Error: {e}")
                st.stop()
            
        if candidates:
            with st.spinner("Ranking candidates via biometric similarity..."):
                try:
                    ranker = CandidateRanker(engine)
                    ranked = ranker.rank_candidates(embedding, candidates)
                    best_evidence = ranker.select_best_evidence(ranked)
                    st.session_state.ranked = ranked
                    st.session_state.best_evidence = best_evidence
                except Exception as e:
                    st.sidebar.error(f"Ranking Error: {e}")
                    st.stop()
                
            if best_evidence:
                with st.spinner("Pinning evidence to IPFS & Generating fingerprints..."):
                    try:
                        resp = requests.get(best_evidence.candidate.image_url, timeout=10, stream=True)
                        resp.raise_for_status()
                        
                        # Size limit check
                        cl = resp.headers.get('Content-Length')
                        if cl and int(cl) > 5 * 1024 * 1024:
                            raise ValueError("Image too large for IPFS upload")
                            
                        image_bytes = resp.content
                        ipfs_client = IPFSClient()
                        ipfs_cid = ipfs_client.pin_image(image_bytes)
                    except RequestException as e:
                        st.error(f"Failed to fetch image for IPFS: {e}")
                        ipfs_cid = "unavailable"
                    except ValueError as e:
                        st.error(str(e))
                        ipfs_cid = "unavailable"
                    except Exception as e:
                        st.error(f"IPFS Error: {e}")
                        ipfs_cid = "unavailable"
                        
                    canonical_evidence = Evidence(
                        source_url=best_evidence.candidate.source_url,
                        ipfs_cid=ipfs_cid,
                        relevant_text=best_evidence.candidate.metadata.get('name', 'Unknown context'),
                        metadata=best_evidence.candidate.metadata
                    )
                    st.session_state.canonical_evidence = canonical_evidence
                    st.session_state.fingerprint = EvidenceFingerprinter.compute_fingerprint(canonical_evidence)
                    st.session_state.stage = 1
        else:
            st.sidebar.error("No candidates discovered.")

# ==========================================
# MAIN DASHBOARD
# ==========================================
if st.session_state.stage >= 1:
    best = st.session_state.best_evidence
    ev = st.session_state.canonical_evidence
    fp = st.session_state.fingerprint
    
    # 2. DISCOVERY & 3. CANDIDATE RANKING
    st.subheader("2. Discovery & 3. Candidate Ranking")
    
    st.success(f"Discovered {len(st.session_state.candidates)} candidate images from web indices.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(best.candidate.image_url, caption="Highest Confidence Match", use_container_width=True)
    with col2:
        st.write("### Top Ranked Evidence")
        st.info(f"**Evidence Match Score:** {best.evidence_match_score:.1f}%")
        st.caption(f"Raw Face Similarity: {best.face_similarity:.4f}")
        st.write(f"**Source URL:** [{best.candidate.source_url}]({best.candidate.source_url})")
        st.write(f"**Context:** {best.candidate.metadata.get('name')}")
        
    st.markdown("---")
    
    # 4. EVIDENCE & 5. FINGERPRINT
    st.subheader("4. Evidence & 5. Fingerprint")
    st.write("Canonical Evidence JSON Structure (IPFS Pinned):")
    st.json(EvidenceFingerprinter.to_canonical_json(ev))
    
    st.write("Stable SHA-256 Evidence Fingerprint:")
    st.code(fp, language="bash")
    
    st.markdown("---")
    
    # 6. BLOCKCHAIN
    st.subheader("6. Blockchain Registration")
    
    blockchain_enabled = bool(Config.RPC_URL and Config.BLOCKCHAIN_PRIVATE_KEY)
    if not blockchain_enabled:
        st.warning("Blockchain verification unavailable. Configure RPC_URL and wallet credentials in .env.")
        
    if st.session_state.tx_hash is None:
        if st.button("Commit to Distributed Ledger", type="primary", disabled=not blockchain_enabled):
            with st.spinner("Executing Web3 Transaction..."):
                try:
                    registry = BlockchainRegistry()
                    tx_hash = registry.register_evidence(fp)
                    st.session_state.tx_hash = tx_hash
                    st.rerun()
                except Exception as e:
                    st.error(f"Ledger Error: {e}")
                    st.caption("Check RPC_URL and private key in .env")
    else:
        st.success("✓ Cryptographic Proof Anchored to Blockchain")
        st.code(f"TX HASH: {st.session_state.tx_hash}", language="bash")
        
        st.markdown("---")
        
        # 7. VERIFICATION
        st.subheader("7. Verification & Tamper Detection")
        
        if not blockchain_enabled:
            st.warning("Verification unavailable. Configure RPC_URL and CONTRACT_ADDRESS in .env.")
        else:
            try:
                registry = BlockchainRegistry()
                verifier = EvidenceVerifier(registry)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Scenario A: Verify Original Evidence**")
                    result_orig = verifier.verify(ev)
                    if result_orig.is_verified:
                        st.success(result_orig.message)
                        st.info(f"Registrar: {result_orig.blockchain_registrar}\n\nTimestamp: {result_orig.blockchain_timestamp}")
                    else:
                        st.error("FAILED")
                        
                with c2:
                    st.write("**Scenario B: Simulate Tampering (Deepfake)**")
                    st.caption("Simulating an OSINT attack where the image binary is replaced (altering the IPFS CID)...")
                    tampered = copy.deepcopy(ev)
                    tampered.ipfs_cid = "QmDeepfakeHash1234567890abcdef1234567890abcdef"
                    result_tampered = verifier.verify(tampered)
                    
                    if not result_tampered.is_verified:
                        st.error(result_tampered.message)
                        st.warning("Tamper detection successfully prevented verification of altered image binary.")
                    else:
                        st.warning("FAILED TO DETECT TAMPERING.")
                        
                st.markdown("---")
                
                # EVIDENCE CHAIN VISUALIZATION
                st.subheader("Evidence Chain Visualization")
                
                dot = graphviz.Digraph(comment='Evidence Chain', format='svg')
                dot.attr(rankdir='LR', size='8,5', bgcolor='transparent')
                dot.attr('node', shape='box', style='filled', color='white', fillcolor='#222222', fontcolor='white', fontname='Courier')
                dot.attr('edge', color='#00FF41')
                
                dot.node('A', 'Target Image')
                dot.node('B', 'Face Embedding')
                dot.node('C', f'{len(st.session_state.candidates)} Candidates')
                dot.node('D', f'Best Match ({best.evidence_match_score:.1f}%)')
                dot.node('E', 'IPFS CID')
                dot.node('F', f'SHA-256:\n{fp[:12]}...')
                dot.node('G', f'Blockchain TX:\n{st.session_state.tx_hash[:12]}...')
                
                dot.edges(['AB', 'BC', 'CD', 'DE', 'EF', 'FG'])
                
                st.graphviz_chart(dot)
                
            except Exception as e:
                st.error(f"Verification Engine Error: {e}")
else:
    if uploaded_file is not None:
        st.info("Target Acquired. Ready to run OSINT Discovery Workflow.")
    else:
        st.info("Awaiting Target Acquisition... Please upload an image in the sidebar.")
