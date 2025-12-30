## What's New in v1.20

### New Features
- **Pubkey Mask Mode** (`-mask`): Match raw pubkey X-coordinate patterns directly
- **Signature R-Value Grinding** (`-sig`): Grind ECDSA/Schnorr nonces for custom R.x values
- **TXID Grinding Mode** (`-txid`): Grind transaction nonce for custom TXID prefixes
- **Arbitrary Mask Positioning** (`-mx`): Match any bit positions, not just prefixes
- **BIP340 Schnorr Support** (`--schnorr`): Taproot-ready signature grinding
- **BIP146 Low-S Normalization**: Automatic for all ECDSA signatures

### Performance
- RTX 4090: ~27 GKey/s for mask/signature modes (EC operations)
- RTX 4090: ~8 MKey/s for TXID mode (double SHA256)

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

**TXID Grinding Mode:**
```bash
# Grind nLockTime (last 4 bytes) for TXID prefix "0000"
./VanitySearch -gpu -txid -raw 0100000001...00000000 -tx 0000 --prefix 2 -stop

# With custom nonce position
./VanitySearch -gpu -txid -raw 0100000001... -tx dead --prefix 2 \
  -nonce-offset 50 -nonce-len 4 -stop
```

### Breaking Changes
None - fully backwards compatible with VanitySearch v1.19
- `-stego` flag still works (alias for `-mask`)

---
Based on [VanitySearch](https://github.com/JeanLucPons/VanitySearch) by Jean Luc Pons.
