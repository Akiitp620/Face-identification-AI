// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EvidenceRegistry {
    struct Evidence {
        bytes32 fingerprint;
        uint256 timestamp;
        address registrar;
    }

    // Maps a SHA-256 fingerprint to its registration record
    mapping(bytes32 => Evidence) private registry;

    event EvidenceRegistered(bytes32 indexed fingerprint, uint256 timestamp, address indexed registrar);

    /**
     * @dev Registers a new piece of evidence via its deterministic fingerprint.
     * Reverts if the fingerprint has already been registered.
     */
    function registerEvidence(bytes32 _fingerprint) public {
        require(registry[_fingerprint].timestamp == 0, "Evidence already registered");
        
        registry[_fingerprint] = Evidence({
            fingerprint: _fingerprint,
            timestamp: block.timestamp,
            registrar: msg.sender
        });
        
        emit EvidenceRegistered(_fingerprint, block.timestamp, msg.sender);
    }

    /**
     * @dev Verifies if a fingerprint exists in the registry.
     * Returns true, along with the timestamp and the registrar's address, if found.
     */
    function verifyEvidence(bytes32 _fingerprint) public view returns (bool exists, uint256 timestamp, address registrar) {
        Evidence memory e = registry[_fingerprint];
        if (e.timestamp > 0) {
            return (true, e.timestamp, e.registrar);
        }
        return (false, 0, address(0));
    }
}
