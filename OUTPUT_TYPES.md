# Bitcoin Output Types for VanityMask

This document analyzes different Bitcoin output types for use with VanityMask grinding modes, focusing on data visibility, tooling compatibility, and practical considerations.

---

## Output Type Comparison

### Overview

When embedding data in a pubkey X coordinate using `-mask` mode, the choice of output type determines **when** and **how** that data becomes visible on-chain.

| Output Type | Data in scriptPubKey | Data on Spend | Core Compatibility | Signature Type |
|-------------|---------------------|---------------|-------------------|----------------|
| P2PKH | Hash only | Witness reveals pubkey | Full | ECDSA |
| **P2WPKH** | Hash only | Witness reveals pubkey | Full | ECDSA |
| P2TR (standard) | Tweaked key | Internal key recoverable | Full | Schnorr |
| P2TR (raw X) | Raw X visible | Same | Manual signing required | Schnorr |

---

## P2WPKH (SegWit v0) - Recommended

**Format:** `OP_0 <20-byte HASH160(pubkey)>`

### Characteristics

```
On receive:  scriptPubKey = 0014<hash160>
             Only a 20-byte hash is visible

On spend:    witness = [<signature>, <compressed_pubkey>]
             Full 33-byte pubkey (with your data) becomes visible
```

### Advantages

1. **Temporal control** - Data only appears when you choose to spend
2. **Maximum commonality** - ~60% of Bitcoin outputs are P2WPKH
3. **Full tooling** - Bitcoin Core handles everything natively
4. **ECDSA signatures** - Enables `-sig` mode R.x grinding when spending
5. **Standard fees** - No witness discount penalties

### Example Workflow

```bash
# 1. Grind pubkey with target prefix
VanitySearch.exe -mask -tx CAFE42 --prefix 3 -gpu -stop
# Output: Privkey 3B558166..., Pubkey X starts with CAFE42

# 2. Derive P2WPKH address
# scriptPubKey: 0014 + HASH160(compressed_pubkey)
# Address: bc1q... (mainnet) or bcrt1q... (regtest)

# 3. Receive funds - data NOT visible on chain
# scriptPubKey shows: 00141d916fca9304748d41921a86fb92de6d2fb8ea47

# 4. Spend when ready - data IS visible
# witness reveals: 02CAFE4277791C0B638F38AF0528F13A6062BB212C...
```

### When to Use

- Default choice for most applications
- When you want control over data reveal timing
- When you need `-sig` mode for additional ECDSA R.x grinding
- When blending in with normal transaction patterns matters

---

## P2TR (Taproot) - Standard Mode

**Format:** `OP_1 <32-byte tweaked_pubkey>`

### The Tweak Mechanism

P2TR uses a key tweaking scheme (BIP-341):

```
Internal key:  Your ground pubkey (CAFE42...)
Tweak:         t = SHA256("TapTweak" || internal_key)
Output key:    Q = P + t*G
```

The **output key** (what goes on-chain) is different from your **internal key** (where your data lives).

### Characteristics

```
On receive:  scriptPubKey = 5120<tweaked_output_key>
             32-byte tweaked key visible (NOT your raw data)

On spend:    Key-path spend reveals nothing extra
             Your internal key data is mathematically recoverable
             but requires knowing the tweak
```

### Advantages

1. **Data separation** - Raw data not directly visible in scriptPubKey
2. **Full tooling** - Bitcoin Core signs normally
3. **Future-proof** - Taproot is the modern standard
4. **Script flexibility** - Can add script paths if needed

### Disadvantages

1. **No ECDSA** - Schnorr signatures only (different grinding)
2. **Data recovery complexity** - Need to reverse tweak to extract data
3. **Less common** - ~10-15% of outputs currently

### When to Use

- When you prefer data not be directly visible even on-chain
- When you need Taproot script features
- When Schnorr signature properties are desired

---

## P2TR (Raw X) - Direct Embedding

**Format:** `OP_1 <32-byte raw_pubkey_X>`

This bypasses the standard tweak and puts your raw X coordinate directly in the scriptPubKey.

### Characteristics

```
On receive:  scriptPubKey = 5120<your_raw_X_coordinate>
             Your data (CAFE42...) immediately visible

On spend:    Requires manual Schnorr signing
             Cannot use Bitcoin Core's built-in signing
```

### Advantages

1. **Immediate visibility** - Data readable directly from scriptPubKey
2. **Simple extraction** - No tweak reversal needed
3. **32 bytes available** - Full X coordinate for data

### Disadvantages

1. **No Core signing** - Must implement BIP-340 Schnorr manually
2. **Complexity** - Custom signing code required
3. **Non-standard** - Violates BIP-341 key derivation

### When to Use

- When immediate on-chain data visibility is required
- When you have custom signing infrastructure
- For special applications where Core compatibility isn't needed

---

## P2PKH (Legacy) - Not Recommended

**Format:** `OP_DUP OP_HASH160 <20-byte hash> OP_EQUALVERIFY OP_CHECKSIG`

### Characteristics

Similar to P2WPKH but without SegWit benefits:
- Larger transaction size
- Higher fees
- Data revealed on spend (in scriptSig)

### When to Use

- Legacy compatibility requirements only
- Generally avoid for new applications

---

## Data Visibility Summary

```
                    On Receive          On Spend
                    ──────────          ────────
P2WPKH              Hash only    →      Pubkey revealed in witness
                    (data hidden)       (data visible)

P2TR (standard)     Tweaked key  →      Same (internal key recoverable)
                    (data obscured)     (with tweak knowledge)

P2TR (raw X)        Raw X        →      Same
                    (data visible)      (data visible)
```

---

## Multi-Channel Encoding

For maximum data density, combine multiple channels:

### Single Transaction Channels

| Channel | Mode | Bits (3-min budget) | Notes |
|---------|------|---------------------|-------|
| Output 0 pubkey | `-mask` | 40 | Primary data |
| Output 1 pubkey | `-mask` | 40 | Additional data |
| Signature R.x | `-sig` | 40 | Per input (ECDSA only) |
| TXID | `-txid` | 24-28 | Via output grinding |

### Workflow Order

```
1. Grind data-bearing pubkeys (mask mode)
2. Build transaction template
3. Grind TXID (via output pubkey modification)
4. Compute sighash
5. Grind signatures (sig mode, if ECDSA)
6. Broadcast
```

---

## Recommendations

### For General Use

**Use P2WPKH.** It provides:
- Control over when data becomes visible
- Full Bitcoin Core compatibility
- ECDSA signature grinding capability
- Maximum commonality with normal transactions

### For Taproot Applications

**Use standard P2TR.** It provides:
- Modern output type
- Data in internal key (not directly visible)
- Full Bitcoin Core compatibility

### For Special Applications

**Use P2TR raw X only if:**
- You need immediate data visibility
- You have custom signing infrastructure
- Core compatibility is not required

---

## Quick Reference

### P2WPKH Address Derivation

```python
from hashlib import sha256, new as hashlib_new

# compressed_pubkey = 02/03 + X coordinate (33 bytes)
sha = sha256(compressed_pubkey).digest()
hash160 = hashlib_new('ripemd160', sha).digest()
# scriptPubKey = 0014 + hash160
# Address = bech32_encode('bc', 0, hash160)
```

### P2TR Address Derivation (Standard)

```python
# internal_key = X coordinate (32 bytes)
tweak = tagged_hash("TapTweak", internal_key)
output_key = point_add(internal_key, tweak * G)
# scriptPubKey = 5120 + output_key.x
# Address = bech32m_encode('bc', 1, output_key.x)
```

---

## Test Results

All output types tested on Bitcoin Core regtest (v28.1.0):

| Output Type | Receive | Spend | Data Recovery |
|-------------|---------|-------|---------------|
| P2WPKH | PASS | PASS | In witness |
| P2TR (standard) | PASS | PASS | Via tweak |
| P2TR (raw X) | PASS | Manual required | Direct |

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for detailed test logs.

---

**Last Updated:** 2024-12-30
