# Bitcoin Output Types for VanityMask

This document analyzes Bitcoin output types for steganographic data encoding with VanityMask, focusing on **immediate data visibility** and spendability.

---

## Quick Reference

| Output Type | X Visible | When | Spendable | Sig Type | Recommended |
|-------------|-----------|------|-----------|----------|-------------|
| **P2PK** | **YES** | **Immediate** | **YES** | ECDSA | **PRIMARY** |
| P2WPKH | No | On spend | Yes | ECDSA | Secondary |
| P2TR (raw) | Yes | Immediate | Manual | Schnorr | Not recommended |
| P2TR (std) | No | Never | Yes | Schnorr | Not recommended |

---

## P2PK (Pay-to-Public-Key) - PRIMARY METHOD

**Format:** `<33-byte compressed pubkey> OP_CHECKSIG`

### Why P2PK?

1. **Immediate visibility** - Pubkey X coordinate is directly in scriptPubKey
2. **Spendable** - Standard ECDSA signing works
3. **R.x grinding** - Can grind signature R.x for additional data
4. **Bitcoin Core compatible** - Full wallet support
5. **What Obscurity uses** - Proven steganographic approach

### scriptPubKey Structure

```
Bytes: 21 02CAFE4277791C0B638F38AF0528F13A6062BB212C8E9B658DF9FEEA8B4BAC05C4 AC
       ^^ ^^                                                                ^^
       |  |                                                                 OP_CHECKSIG (0xAC)
       |  33-byte compressed pubkey (02/03 prefix + 32-byte X coordinate)
       OP_PUSHBYTES_33 (0x21)

Data location: Bytes 2-33 (the X coordinate)
Data capacity: 32 bytes (256 bits) per output
```

### Channel Capacity

| Channel | Capacity | Visibility | Notes |
|---------|----------|------------|-------|
| Pubkey X | **256 bits/output** | Immediate | Full X coordinate |
| Signature R.x | 40 bits/input | Immediate | ECDSA nonce grinding |
| TXID prefix | 28 bits/tx | Immediate | Transaction hash |
| Y parity | 1 bit/output | Immediate | 02 vs 03 prefix |

### Example Workflow

```bash
# 1. Grind pubkey with target X prefix (or full X for max data)
VanitySearch.exe -mask -tx CAFE4277 --prefix 4 -gpu -stop
# Output: Privkey, Pubkey X = CAFE4277...

# 2. Create P2PK scriptPubKey
# scriptPubKey = 0x21 + compressed_pubkey + 0xAC

# 3. Fund the P2PK output (raw transaction or Bitcoin Core)

# 4. Data is IMMEDIATELY visible in the output scriptPubKey
```

### Transaction Configurations

#### Option A: Single Output (256 bits)
```
1-in, 1-out P2PK transaction

  Input 0:  [funding UTXO]
  Output 0: P2PK with ground pubkey

  Data: 256 bits in pubkey X
  Bonus: 40 bits in signature R.x (if grinding)
  Bonus: 28 bits in TXID (if grinding)
```

#### Option B: Multi-Output (768+ bits)
```
1-in, 3-out P2PK transaction

  Input 0:  [funding UTXO]
  Output 0: P2PK = 256 bits
  Output 1: P2PK = 256 bits
  Output 2: P2PK = 256 bits

  Total: 768 bits (96 bytes) in pubkey X alone
  Bonus: +40 bits signature, +28 bits TXID
```

---

## P2WPKH (SegWit v0) - SECONDARY METHOD

**Format:** `OP_0 <20-byte HASH160(pubkey)>`

### When to Use P2WPKH

- **Delayed reveal** - Data hidden until you choose to spend
- **Maximum blending** - Most common output type (~60% of outputs)
- **SegWit savings** - Lower fees due to witness discount
- **Privacy feature** - Control when data becomes visible

### Visibility Timeline

```
On creation:  scriptPubKey = 0014 <20-byte hash>
              Data: HIDDEN (only hash visible)

On spend:     witness = [signature, compressed_pubkey]
              Data: REVEALED (pubkey X now visible)
```

### Use Cases

1. **Two-phase commit** - Create now, reveal later
2. **Plausible deniability** - "Just a normal address"
3. **Coinjoin preparation** - Hide data until mixed

### Channel Capacity (P2WPKH)

| Channel | Capacity | When Visible |
|---------|----------|--------------|
| Pubkey X | 256 bits/output | On spend |
| Signature R.x | 40 bits/input | On spend |
| TXID prefix | 28 bits/tx | Immediate |

---

## P2TR (Taproot) - NOT RECOMMENDED

### P2TR Standard (with tweak)

The standard Taproot key derivation applies a tweak:

```
Internal key:  Your ground pubkey (CAFE42...)
Tweak:         t = SHA256("TapTweak" || internal_key)
Output key:    P + t*G = DIFFERENT VALUE
```

**Problem:** Your ground X coordinate is mathematically obscured.

### P2TR Raw X (no tweak)

Putting raw X in scriptPubKey:

```
scriptPubKey: 5120 <32-byte raw X>
```

**Problem:** Bitcoin Core won't sign correctly (expects tweaked key). Requires custom BIP-340 Schnorr signing implementation.

### Why Not Taproot?

1. Schnorr signatures (can't grind R.x with VanityMask's ECDSA mode)
2. Key tweaking obscures your data
3. Raw X requires custom signing code

---

## Comparison Summary

### For Immediate Visibility (Sidechain Proofs)

**Use P2PK.** Your pubkey X is directly in the scriptPubKey, visible as soon as the transaction is broadcast.

### For Delayed Visibility (Privacy/Coinjoin)

**Use P2WPKH.** Your pubkey X is hidden in a hash until you spend, giving you control over reveal timing.

### For Maximum Data Per Transaction

| Config | Pubkey X | Sig R.x | TXID | Total |
|--------|----------|---------|------|-------|
| 1-in, 1-out P2PK | 256 | 40 | 28 | **324 bits** |
| 1-in, 2-out P2PK | 512 | 40 | 28 | **580 bits** |
| 1-in, 3-out P2PK | 768 | 40 | 28 | **836 bits** |
| 2-in, 3-out P2PK | 768 | 80 | 28 | **876 bits** |

---

## P2PK Address Derivation

P2PK outputs don't have a standard address format (they predate addresses). Use raw scriptPubKey:

```python
# From compressed pubkey to P2PK scriptPubKey
compressed_pubkey = bytes.fromhex('02CAFE4277...')  # 33 bytes
script_pubkey = bytes([0x21]) + compressed_pubkey + bytes([0xAC])

# To spend: sign with ECDSA, put signature in scriptSig
# scriptSig = <signature>
```

---

## Test Results

### P2PK on Bitcoin Core Regtest

| Test | Result | Details |
|------|--------|---------|
| Create P2PK output | PASS | scriptPubKey contains raw pubkey |
| X visible immediately | PASS | Can read CAFE42... from script |
| Spend P2PK output | PASS | ECDSA signature works |
| R.x grinding on spend | PASS | Signature R.x prefix matched |

### P2WPKH on Bitcoin Core Regtest

| Test | Result | Details |
|------|--------|---------|
| Create P2WPKH output | PASS | Hash only in scriptPubKey |
| X hidden until spend | PASS | Cannot see pubkey in output |
| Spend reveals pubkey | PASS | Witness contains full pubkey |

---

## Recommendations

### Steganographic Sidechain (Immediate Proofs)

```
Use P2PK outputs:
- 1 output = 256 bits = full sidechain block hash
- Data visible immediately for verifiers
- Spendable (not a burn address)
- Grind signature R.x for bonus 40 bits
```

### Privacy-Focused Encoding

```
Use P2WPKH outputs:
- Data hidden until you spend
- Blend with 60% of Bitcoin outputs
- SegWit fee savings
- Reveal on your schedule
```

### Maximum Throughput

```
3-out P2PK + signature grinding:
- 768 bits in pubkey X (3 outputs)
- 40 bits in signature R.x
- 28 bits in TXID
- Total: 836 bits (104.5 bytes) per transaction
```

---

**Last Updated:** 2024-12-30
**Primary Method:** P2PK (immediate visibility)
**Secondary Method:** P2WPKH (delayed visibility)
