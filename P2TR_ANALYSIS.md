# P2TR (Taproot) Analysis for Steganographic Data Embedding

An analysis of whether Taproot outputs can be used for steganographic data encoding with VanityMask.

---

## TL;DR

| Approach | Data Visible | When | Spendable | VanityMask Support |
|----------|--------------|------|-----------|-------------------|
| **P2PK** | **YES** | **Immediate** | Yes (ECDSA) | **FULL** |
| P2TR (rawtr) | YES | Immediate | Yes (Schnorr) | **NO** (needs work) |
| P2TR (tr) | No | Script path spend | Yes (Schnorr) | **NO** |
| P2WPKH | No | Key reveal spend | Yes (ECDSA) | FULL |

**Verdict:** P2TR with tweaking fundamentally hides the internal key. Raw P2TR could work but requires Schnorr signature support that VanityMask doesn't have.

---

## The Taproot Tweak Problem

### Standard P2TR Key Derivation (BIP-341)

```
Internal Key:  P (your ground pubkey with data prefix CAFE42...)
Tweak:         t = SHA256("TapTweak" || P)
Output Key:    Q = P + t*G

scriptPubKey:  5120 <Q>  (OP_1 OP_PUSHBYTES_32 <output_key>)
```

**The Problem:** Q is what appears on-chain, NOT P. Your CAFE42 prefix is mathematically scrambled into an unrecognizable value.

### Example

```
Internal Key P:    CAFE4277791C0B638F38AF0528F13A6062BB212C8E9B658DF9FEEA8B4BAC05C4
Tweak t:           3A7B... (hash of P)
Output Key Q:      8F21D9E3... (completely different - your data is HIDDEN)
```

**Verifier sees:** `5120 8F21D9E3...` - No CAFE42 prefix visible!

---

## Is the Tweak Reversible?

**NO.** The tweak is a one-way hash function:

```
t = SHA256("TapTweak" || P)
```

Given only Q (the output key), you cannot recover P (the internal key) because:
1. You don't know t
2. t depends on P
3. You can't solve Q = P + t*G without knowing either P or t

**BUT:** If the verifier knows P ahead of time (out-of-band), they CAN verify:
```python
# Verifier knows P from sidechain protocol
t = tagged_hash("TapTweak", P)
Q_expected = P + t*G
assert Q_expected == Q_from_scriptPubKey  # Verification passes
```

This is the "commit-reveal" pattern - you commit to P via Q, then reveal P later.

---

## Can We "Finesse" P2TR for Immediate Visibility?

### Option 1: Raw P2TR (rawtr descriptor)

Bitcoin Core supports `rawtr(KEY)` which puts KEY directly as the output key WITHOUT tweaking:

```
scriptPubKey:  5120 <KEY>  (no tweak applied)
```

**Advantages:**
- KEY is immediately visible in scriptPubKey
- Same 256-bit capacity as P2PK

**Disadvantages:**
- Requires **Schnorr signatures** (BIP-340), not ECDSA
- VanityMask's `-sig` mode only supports ECDSA nonce grinding
- Cannot prove no hidden script path exists (security concern)
- Less common, may stand out

### Option 2: P2TR with Out-of-Band P Disclosure

Use standard P2TR but share P separately:

```
On-chain:      5120 <Q>  (tweaked output key)
Out-of-band:   Internal key P = CAFE4277...
Verification:  Confirm Q = P + hash(P)*G
```

**For sidechain use:** Sidechain block header includes P. Anyone can verify Q matches.

**Disadvantages:**
- Requires extra protocol layer
- P not directly readable from blockchain alone

### Option 3: Script Path Reveal

Create P2TR with a script tree, spend via script path:

```
On creation:   5120 <Q>  - P hidden
On spend:      Control block reveals P, merkle path
After spend:   P visible in witness
```

**Same problem as P2WPKH:** Data only visible after spending.

---

## Schnorr Signature Grinding (Future Work)

### Schnorr Signature Structure (BIP-340)

```
Signature: R || s  (64 bytes total)
  R = 32-byte x-coordinate of nonce point (k*G)
  s = 32-byte scalar
```

**Theoretically:** We could grind nonce `k` until `R = k*G` has desired prefix, just like ECDSA.

**Current Status:** VanityMask's GPU kernel for signature mode is ECDSA-specific:
- ECDSA: `s = k^(-1) * (z + r*d) mod n`
- Schnorr: `s = k + e*d mod n` where `e = hash(R || P || m)`

**Implementation Required:**
1. Add BIP-340 Schnorr signing to GPU kernel
2. Modify nonce grinding loop for Schnorr formula
3. Handle x-only pubkey encoding

**Estimated effort:** Moderate (formula change, but same EC operations)

---

## Throughput Comparison

Assuming we implement Schnorr support:

| Output Type | Pubkey X | Sig R | TXID | Total | Visibility |
|-------------|----------|-------|------|-------|------------|
| P2PK | 256 | 40 (ECDSA) | 28 | 324 | Immediate |
| P2TR (rawtr) | 256 | 256 (Schnorr) | 28 | 540 | Immediate |
| P2WPKH | 256 | 40 (ECDSA) | 28 | 324 | On spend |

**Note:** Schnorr signatures are 64 bytes with full 32-byte R (vs. ECDSA's variable-length DER encoding). Could theoretically grind more bits in R.

---

## Mathematical Deep Dive

### Why the Tweak Hides Data

```python
# BIP-341 tweak computation
def taproot_tweak(internal_key: bytes, merkle_root: bytes = b'') -> int:
    tag = b'TapTweak'
    tag_hash = sha256(tag)
    data = internal_key + merkle_root
    return int.from_bytes(sha256(tag_hash + tag_hash + data), 'big') % n

# Output key computation
P = internal_pubkey_point  # Contains our data in X coordinate
t = taproot_tweak(P.x.to_bytes(32, 'big'))
Q = P + t * G  # Output key - data is scrambled
```

The tweak `t` depends on `P`, creating a feedback loop that makes P unrecoverable from Q alone.

### The Algebraic Barrier

Given Q and wanting to find P:
```
Q = P + hash(P)*G
```

This is not a standard discrete log problem - it's worse. You'd need to:
1. Guess P
2. Compute hash(P)*G
3. Check if P + hash(P)*G = Q

There's no shortcut. You must know P to verify it matches Q.

---

## Recommendation

### For Immediate Data Visibility

**Use P2PK (current recommendation).**

- Data visible immediately in scriptPubKey
- ECDSA signing fully supported
- VanityMask has complete support
- Regtest verified

### For Future P2TR Support

If P2TR is required (e.g., for fee savings, blending with modern outputs):

1. **Short-term:** Use `rawtr()` with manual Schnorr signing (outside VanityMask)
2. **Medium-term:** Implement Schnorr nonce grinding in VanityMask GPU kernel
3. **Alternative:** Use P2TR with out-of-band P disclosure for sidechain verification

### Not Recommended

- Standard P2TR (`tr()`) for immediate data visibility - the tweak hides your data
- Relying on script path reveal - same limitation as P2WPKH

---

## Quick Reference

### P2PK (WORKS NOW)

```bash
# Grind pubkey
VanitySearch.exe -mask -tx CAFE4277 --prefix 4 -gpu -stop

# scriptPubKey (immediate visibility)
# 21 02cafe4277... ac
```

### P2TR rawtr (FUTURE)

```bash
# Would need Schnorr support
VanitySearch.exe -mask -tx CAFE4277 --prefix 4 -gpu -stop
# Then use rawtr(KEY) descriptor with manual Schnorr signing

# scriptPubKey (immediate visibility)
# 5120 cafe4277...
```

### P2TR standard (NOT USEFUL)

```
# Internal key with data prefix
P = CAFE4277...

# Output key (data hidden!)
Q = P + hash(P)*G = 8F21D9E3...  # CAFE42 prefix GONE
```

---

## Sources

- [BIP-341: Taproot](https://en.bitcoin.it/wiki/BIP_0341) - Key tweaking specification
- [BIP-340: Schnorr Signatures](https://en.bitcoin.it/wiki/BIP_0340) - Signature algorithm
- [BIP-386: tr() Descriptors](https://bips.dev/386/) - Descriptor format
- [Bitcoin Core rawtr() PR](https://github.com/bitcoin/bitcoin/pull/23480) - Raw Taproot descriptor

---

**Conclusion:** P2TR's tweaking mechanism fundamentally prevents immediate data visibility. P2PK remains the best choice for steganographic sidechain proofs with VanityMask.

**Last Updated:** 2024-12-31
