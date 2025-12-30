# Changelog

All notable changes to VanityMask will be documented in this file.

## [1.20] - 2025-12-29

### Added
- **Pubkey Mask Mode** (`-mask`): Match raw pubkey X-coordinate patterns at any bit position
- **Signature R-Value Grinding** (`-sig`): Grind ECDSA/Schnorr nonces for target R.x patterns
- **TXID Grinding Mode** (`-txid`): Grind transaction nonce for custom TXID prefixes
- **Arbitrary Mask Positioning** (`-mx`): Match any bit positions, not just prefix
- **BIP340 Schnorr Support** (`--schnorr`): Y-parity handling for Taproot signatures
- **BIP146 Low-S Normalization**: Automatic for all ECDSA signatures

### Changed
- Renamed `-stego` to `-mask` (old flag still works for compatibility)
- Updated CUDA support to 13.0
- Updated Visual Studio toolset to v143 (VS 2022)
- Removed deprecated SM architectures (sm_50, sm_60, sm_70)

### Performance
- RTX 4090: ~27 GKey/s for mask/signature modes (EC operations)
- RTX 4090: ~8 MKey/s for TXID mode (double SHA256)
- Same kernel for mask/sig modes (pure EC point multiplication)
- 3-4x faster than address mode for EC operations (no hashing overhead)

### Technical Details
- ComputeKeysMask GPU kernel for direct X-coordinate matching
- grind_txid_kernel for transaction ID grinding with double SHA256
- ModInvOrder helper for modular inverse mod curve order
- Signature computation: s = k^(-1) * (z + r*d) mod n
- TXID = SHA256(SHA256(raw_tx)) with configurable nonce position

## [1.19] - Original VanitySearch

Based on [JeanLucPons/VanitySearch](https://github.com/JeanLucPons/VanitySearch) v1.19

### Features (inherited)
- Bitcoin vanity address generation (P2PKH, P2SH, BECH32)
- Multi-GPU CUDA support
- CPU parallelization with SSE
- Split-key vanity generation
- Wildcard pattern matching
- Case-insensitive search
