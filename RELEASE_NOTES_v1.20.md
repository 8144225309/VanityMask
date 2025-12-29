## What's New in v1.20

### New Features
- **Pubkey Mask Mode** (`-mask`): Match raw pubkey X-coordinate patterns directly
- **Signature R-Value Grinding** (`-sig`): Grind ECDSA/Schnorr nonces for custom R.x values
- **Arbitrary Mask Positioning** (`-mx`): Match any bit positions, not just prefixes
- **BIP340 Schnorr Support** (`--schnorr`): Taproot-ready signature grinding
- **BIP146 Low-S Normalization**: Automatic for all ECDSA signatures

### Performance
- RTX 4090: ~27 GKey/s for mask/signature modes
- 3-4x faster than address mode (no SHA256/RIPEMD160 overhead)

### Compatibility
- Windows: Visual Studio 2022, CUDA 13.0
- Linux: GCC, CUDA 12.0+
- Tested on RTX 4090, RTX 3080

### Usage Examples

**Pubkey Mask Mode:**
```bash
./VanitySearch -gpu -mask -tx DEADBEEF --prefix 4 -stop
```

**Signature R-Value Grinding:**
```bash
./VanitySearch -gpu -sig -tx DEADBEEF --prefix 4 \
  -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 \
  -d 0000000000000000000000000000000000000000000000000000000000000001
```

### Breaking Changes
None - fully backwards compatible with VanitySearch v1.19
- `-stego` flag still works (alias for `-mask`)

---
Based on [VanitySearch](https://github.com/JeanLucPons/VanitySearch) by Jean Luc Pons.
