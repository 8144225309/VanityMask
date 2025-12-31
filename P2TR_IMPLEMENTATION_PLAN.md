# P2TR Support Implementation Plan

Analysis of what's needed to add full Taproot support to VanityMask.

---

## Current State

### What Exists

VanityMask already has `--schnorr` flag but it's **INCOMPLETE**:

```cpp
// Vanity.cpp lines 1769-1806 (current implementation)

// Only handles R.y parity for x-only pubkeys:
if (schnorrMode && pubKey.y.IsOdd()) {
    nonce_k.Neg();  // Negate k if R.y is odd
}

// BUT signature computation is still ECDSA formula:
s = k^-1 * (z + r*d) mod n   // WRONG for Schnorr!
```

### What's Missing for Full Schnorr

The BIP-340 Schnorr signature formula is:
```
e = SHA256_tagged("BIP0340/challenge", R.x || P.x || m)
s = k + e*d mod n   // Note: NO modular inverse!
```

Current code computes ECDSA `s = k^-1 * (z + r*d)` which is wrong.

---

## Three Implementation Options

### Option A: Post-Tweak Pubkey Grinding (New Mode)

**Use Case:** Standard P2TR with tr(KEY) - data visible in tweaked output key Q

**Algorithm:**
```
for each candidate privkey d:
    P = d * G
    t = SHA256_tagged("TapTweak", P.x)
    Q = P + t * G
    if Q.x starts with target:
        FOUND!
```

**Changes Required:**

| File | Change |
|------|--------|
| `main.cpp` | Add `-taproot` or `-p2tr` flag |
| `Vanity.h` | Add `taprootMode` bool member |
| `Vanity.cpp` | Add TapTweak tagged hash computation |
| `Vanity.cpp` | Add second EC mult (t*G) and point add (P + t*G) |
| `Vanity.cpp` | Check Q.x instead of P.x for prefix match |
| `GPUEngine.cu` | Add GPU kernel for post-tweak check |

**Performance Impact:** ~2x slower (second EC mult dominates)
- Current: ~27 GKeys/s
- Post-tweak: ~13-15 GKeys/s

**Complexity:** MODERATE

---

### Option B: Fix Schnorr Signature Mode

**Use Case:** rawtr() outputs with proper Schnorr spending

**Current State:** R.x grinding works, but s computation is wrong

**Fix Required:**

```cpp
// Current (ECDSA - wrong for Schnorr):
k_inv = ModInv(k)
s = k_inv * (z + r*d)

// Correct (BIP-340 Schnorr):
e = SHA256_tagged("BIP0340/challenge", R.x || P.x || m)
s = k + e*d mod n
```

**Changes Required:**

| File | Change |
|------|--------|
| `Vanity.cpp` | Add BIP-340 tagged hash for challenge |
| `Vanity.cpp` | Replace s computation in schnorrMode |
| `Vanity.cpp` | Add pubkey X as input parameter |
| `main.cpp` | Add `-p` parameter for signing pubkey |

**Performance Impact:** FASTER (no modular inverse in Schnorr)

**Complexity:** LOW

---

### Option C: Combined Taproot Mode

**Use Case:** Full P2TR workflow with both pubkey Q and signature R grinding

**Combines:**
1. Post-tweak pubkey grinding (Option A)
2. Correct Schnorr signature (Option B)

**New Workflow:**
```bash
# Step 1: Grind pubkey for output key Q prefix
VanitySearch.exe -taproot -tx CAFE4277 --prefix 4 -gpu -stop
# Outputs: privkey d, internal key P.x, output key Q.x = CAFE4277...

# Step 2: When spending, grind signature R.x
VanitySearch.exe -sig -schnorr -tx DEADBEEF --prefix 4 \
    -z <sighash> -d <privkey> -p <pubkey_x> -gpu -stop
# Outputs: nonce k, R.x = DEADBEEF..., s
```

**Complexity:** MODERATE (sum of A + B)

---

## Detailed Code Analysis

### Tagged Hash (Required for Both Options)

BIP-340 and BIP-341 use tagged hashes:

```cpp
// Already exists in GPUEngine.cu for TXID mode, need CPU version too
void TaggedHash(const char* tag, const uint8_t* data, size_t len, uint8_t* out) {
    // tag_hash = SHA256(tag)
    uint8_t tag_hash[32];
    sha256(tag, strlen(tag), tag_hash);

    // result = SHA256(tag_hash || tag_hash || data)
    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, tag_hash, 32);
    sha256_update(&ctx, tag_hash, 32);
    sha256_update(&ctx, data, len);
    sha256_final(&ctx, out);
}
```

### Schnorr s-Value Fix (Option B)

```cpp
// Replace lines 1776-1806 in Vanity.cpp when schnorrMode is true:

if (schnorrMode) {
    // BIP-340 Schnorr signature
    // e = SHA256_tagged("BIP0340/challenge", R.x || P.x || m)
    uint8_t challenge_data[96];  // 32 + 32 + 32
    memcpy(challenge_data, pubKey.x.GetBytes(), 32);      // R.x
    memcpy(challenge_data + 32, sigPubKey.GetBytes(), 32); // P.x (new param)
    memcpy(challenge_data + 64, sigMsgHash.GetBytes(), 32); // m

    uint8_t e_bytes[32];
    TaggedHash("BIP0340/challenge", challenge_data, 96, e_bytes);
    Int e;
    e.SetBytes(e_bytes);
    e.Mod(&secp->order);

    // s = k + e*d mod n (no inverse!)
    s_val.Set(&e);
    s_val.ModMulK1order(&sigPrivKey);
    s_val.ModAddK1order(&nonce_k);

    // No low-s normalization for Schnorr (BIP-340 handles differently)
} else {
    // Existing ECDSA code...
}
```

### Post-Tweak Grinding (Option A)

```cpp
// In Vanity.cpp FindKeyGPU/FindKeyCPU after computing pubKey:

if (taprootMode) {
    // Compute tweaked output key Q = P + hash(P)*G
    uint8_t tweak_data[32];
    TaggedHash("TapTweak", pubKey.x.GetBytes(), 32, tweak_data);

    Int t;
    t.SetBytes(tweak_data);
    t.Mod(&secp->order);

    Point tG = secp->ComputePublicKey(&t);
    Point Q = secp->AddPoints(pubKey, tG);

    // Check Q.x for prefix match instead of P.x
    checkPrefix = Q.x;  // Modified prefix check
}
```

---

## GPU Kernel Considerations

### Post-Tweak Mode

The main loop in `GPUEngine.cu` computes P = d*G and checks P.x prefix.

For post-tweak, we need:
1. Compute P = d*G (existing)
2. Compute t = TaggedHash("TapTweak", P.x) (add SHA256)
3. Compute t*G (add EC scalar mult - EXPENSIVE)
4. Compute Q = P + t*G (add point addition)
5. Check Q.x prefix (modify existing)

**Challenge:** Steps 2-4 roughly double the work per candidate.

**Optimization Opportunity:**
- The "TapTweak" tag hash can be precomputed (constant)
- Use EC batch operations if possible

### Signature Mode

Currently on CPU after GPU finds matching k. The Schnorr vs ECDSA difference is just in s computation - no GPU changes needed.

---

## Recommended Implementation Order

### Phase 1: Fix Schnorr Signature Mode (Quick Win)

1. Add `-p <pubkey_x>` parameter for signing pubkey
2. Add TaggedHash function for CPU
3. Fix s computation when `--schnorr` is set
4. Test with rawtr() outputs

**Effort:** 1-2 hours
**Impact:** Enables rawtr() steganography with proper Schnorr

### Phase 2: Add Post-Tweak Grinding Mode

1. Add `-taproot` flag
2. Add TapTweak computation in CPU path
3. Modify prefix matching to use Q.x
4. Test with standard tr() outputs

**Effort:** 4-6 hours
**Impact:** Enables standard P2TR steganography

### Phase 3: GPU Optimization (Optional)

1. Add TapTweak to GPU kernel
2. Add second EC mult on GPU
3. Benchmark and optimize

**Effort:** 8-16 hours
**Impact:** ~2x faster post-tweak grinding

---

## Summary Table

| Feature | Effort | Performance | Use Case |
|---------|--------|-------------|----------|
| Fix --schnorr s-value | LOW | Same | rawtr() sig grinding |
| Add -taproot mode (CPU) | MODERATE | 2x slower | Standard tr() outputs |
| Add -taproot mode (GPU) | HIGH | ~15 GKeys/s | Faster tr() outputs |

---

## Open Questions

1. **Do we need both tr() and rawtr() support?**
   - tr() is more standard/common
   - rawtr() is simpler but unusual

2. **Should post-tweak grinding be CPU-only initially?**
   - Faster to implement
   - ~500K keys/s on CPU vs ~15M on GPU
   - May be acceptable for 32-bit prefixes

3. **Priority: Schnorr signature fix vs post-tweak grinding?**
   - Schnorr fix is quick and enables rawtr()
   - Post-tweak enables standard tr() but is more work

---

## Current Implementation Status (2024-12-31)

### ✅ Phase 1: Schnorr Signature Mode - COMPLETE

**Implemented:**
- `-p <pubkey_x>` parameter for signing pubkey
- `TaggedHash()` helper function for BIP-340/341 tagged hashes
- Correct BIP-340 Schnorr `s = k + e*d mod n` formula
- R.y parity handling (negate k if R.y is odd)

**Verified:**
```bash
VanitySearch -sig --schnorr -tx DEAD --prefix 2 \
  -z AAAA...64_hex -d BBBB...64_hex -p CCCC...64_hex -gpu -stop
```

Python verification confirms:
- R.x matches k*G.x ✓
- s = k + e*d mod n ✓
- Schnorr verification s*G == R + e*P ✓

### ⏳ Phase 2: Post-Tweak Grinding - PARTIALLY COMPLETE

**Implemented:**
- `-taproot` flag parsing
- Target Q.x parsing and difficulty calculation
- `TaggedHash("TapTweak", P.x)` computation in output handler

**NOT Implemented (requires GPU kernel modification):**
- GPU kernel currently matches P.x, not Q.x
- Need to add in GPUEngine.cu:
  1. Compute t = SHA256_tagged("TapTweak", P.x)
  2. Compute t*G (second EC scalar mult)
  3. Compute Q = P + t*G (point addition)
  4. Compare Q.x against target instead of P.x

**Current Behavior:**
Running `-taproot` shows a clear error message with workaround instructions.

### Workaround for P2TR

Until GPU kernel is modified, use `rawtr()`:

```bash
# 1. Grind pubkey with standard mask mode
VanitySearch -mask -tx CAFE42 --prefix 3 -gpu -stop
# Output: privkey, pubkey_x = CAFE42...

# 2. Create rawtr() output (no tweak)
# bitcoin-cli -regtest importdescriptors '[{"desc":"rawtr(PRIVKEY)#checksum",...}]'
# The scriptPubKey will be: 5120 CAFE42...

# 3. When spending, use Schnorr signature grinding
VanitySearch -sig --schnorr -tx DEADBE --prefix 3 \
  -z <sighash> -d <privkey> -p <pubkey_x> -gpu -stop
```

---

**Last Updated:** 2024-12-31
