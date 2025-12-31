# Taproot GPU Implementation

Technical documentation for the taproot post-tweak grinding GPU kernel.

---

## Overview

Taproot (BIP-341) uses a tweaked public key: `Q = P + hash(P)*G` where the tweak `t = SHA256_tagged("TapTweak", P.x)`.

For steganographic applications, we want to find a private key `d` such that the **output key Q.x** (not the internal key P.x) has a target prefix.

---

## Algorithm

```
Input: target Q.x prefix
Output: private key d, internal key P, output key Q

For each candidate private key d:
    1. P = d * G                           (standard EC point mult)
    2. t = SHA256_tagged("TapTweak", P.x)  (BIP-341 tagged hash)
    3. tG = t * G                          (scalar multiplication)
    4. Q = P + tG                          (point addition)
    5. If Q.x matches target prefix:
         FOUND!
```

---

## GPU Implementation Strategy

### Challenge: Arbitrary Scalar Multiplication

The existing GPU code uses **precomputed generator multiples** for batched point addition:
- `Gx[], Gy[]` store `G, 2G, 3G, ..., 512G`
- Each thread computes `P = start + i*G` using batched additions

For taproot, we need **arbitrary scalar multiplication** `t*G` where `t` comes from SHA256. This requires a different approach.

### Solution: Windowed Scalar Multiplication

Use a 4-bit window method:
1. Precompute table: `[0, G, 2G, ..., 15G]` in constant memory
2. Process scalar 4 bits at a time (64 iterations for 256 bits)
3. Each iteration: lookup + point addition + 4 point doublings

**Performance impact:** ~150 point operations per candidate (vs 2-3 for mask mode)

---

## New GPU Functions

### 1. SHA256_ComputeTagged

```cuda
// Computes: SHA256(SHA256(tag) || SHA256(tag) || data)
__device__ void SHA256_ComputeTagged(uint32_t result[8],
                                     uint64_t px[4],  // 32-byte X coordinate
                                     uint32_t tagHash[8]) {
    // tagHash is precomputed SHA256("TapTweak") in constant memory
    uint32_t state[8];
    SHA256Initialize(state);

    // Block 1: tagHash || tagHash (64 bytes)
    uint32_t w[16];
    memcpy(w, tagHash, 32);
    memcpy(w + 8, tagHash, 32);
    SHA256Transform(state, w);

    // Block 2: px || padding
    // Convert px (4x uint64) to 8x uint32 big-endian
    // Add SHA256 padding
    SHA256Transform(state, w);

    memcpy(result, state, 32);
}
```

### 2. ScalarMultWindow4

```cuda
// Windowed scalar multiplication: result = scalar * G
__device__ void ScalarMultWindow4(uint64_t Rx[4], uint64_t Ry[4],
                                  uint64_t scalar[4]) {
    // Initialize to point at infinity
    bool isInfinity = true;

    // Process 4 bits at a time (64 windows)
    for (int i = 63; i >= 0; i--) {
        // Double 4 times (skip first iteration)
        if (!isInfinity) {
            PointDouble(Rx, Ry);
            PointDouble(Rx, Ry);
            PointDouble(Rx, Ry);
            PointDouble(Rx, Ry);
        }

        // Extract 4-bit window
        int windowIndex = (scalar[i/16] >> ((i%16) * 4)) & 0xF;

        // Add precomputed point
        if (windowIndex != 0) {
            if (isInfinity) {
                Load256(Rx, WINDOW_X[windowIndex]);
                Load256(Ry, WINDOW_Y[windowIndex]);
                isInfinity = false;
            } else {
                PointAdd(Rx, Ry, WINDOW_X[windowIndex], WINDOW_Y[windowIndex]);
            }
        }
    }
}
```

### 3. PointAddAffine

```cuda
// Add two affine points: R = A + B
__device__ void PointAddAffine(uint64_t Rx[4], uint64_t Ry[4],
                               uint64_t Ax[4], uint64_t Ay[4],
                               uint64_t Bx[4], uint64_t By[4]) {
    uint64_t dx[4], dy[4], s[4], s2[4];

    // s = (By - Ay) / (Bx - Ax)
    ModSub256(dx, Bx, Ax);
    ModSub256(dy, By, Ay);
    _ModInv(dx);
    _ModMult(s, dy, dx);

    // Rx = s^2 - Ax - Bx
    _ModSqr(s2, s);
    ModSub256(Rx, s2, Ax);
    ModSub256(Rx, Rx, Bx);

    // Ry = s*(Ax - Rx) - Ay
    ModSub256(dy, Ax, Rx);
    _ModMult(Ry, s, dy);
    ModSub256(Ry, Ry, Ay);
}
```

### 4. ComputeKeysTaproot

```cuda
__device__ void ComputeKeysTaproot(uint64_t *startx, uint64_t *starty,
                                   uint32_t maxFound, uint32_t *out) {
    // Same batched iteration as ComputeKeysStego
    for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {
        // ... batched point addition loop ...

        // For each candidate point P(px, py):

        // 1. Compute tweak hash
        uint32_t tweakHash[8];
        SHA256_ComputeTagged(tweakHash, px, _taptweak_tag_hash);

        // 2. Convert hash to scalar
        uint64_t t[4];
        HashToScalar(t, tweakHash);

        // 3. Compute t*G
        uint64_t tGx[4], tGy[4];
        ScalarMultWindow4(tGx, tGy, t);

        // 4. Compute Q = P + t*G
        uint64_t Qx[4], Qy[4];
        PointAddAffine(Qx, Qy, px, py, tGx, tGy);

        // 5. Check Q.x against target
        CheckStegoPoint(Qx, incr, maxFound, out);
    }
}
```

---

## Constant Memory

```cuda
// Precomputed SHA256("TapTweak")
__device__ __constant__ uint32_t _taptweak_tag_hash[8] = {
    0xe80fe1fe, 0x..., // Actual values computed at init
};

// Window table for scalar multiplication (16 points)
__device__ __constant__ uint64_t WINDOW_X[16][4];
__device__ __constant__ uint64_t WINDOW_Y[16][4];
```

---

## Performance Analysis

| Operation | Count per Point | Relative Cost |
|-----------|-----------------|---------------|
| Batched point add (current) | 1 | 1x |
| SHA256 tagged hash | 2 transforms | ~0.5x |
| 4-bit window scalar mult | 64 doublings + ~16 adds | ~80x |
| Final point addition | 1 | 1x |
| **Total** | | **~82x slower** |

### Expected Throughput

| Mode | Rate | 32-bit Time | 40-bit Time |
|------|------|-------------|-------------|
| Mask | 27 GKey/s | 0.15s | 45s |
| Taproot | 330 MKey/s | 13s | 55 min |

---

## Files Modified

| File | Changes |
|------|---------|
| `GPU/GPUHash.h` | Add `SHA256_ComputeTagged()` |
| `GPU/GPUCompute.h` | Add scalar mult, point ops, taproot kernel |
| `GPU/GPUEngine.cu` | Add `comp_keys_taproot()` wrapper |
| `GPU/GPUEngine.h` | Add `LaunchTaproot()` declaration |
| `GPUEngine.cpp` | Add `LaunchTaproot()` implementation |
| `Vanity.cpp` | Call taproot launch path |
| `main.cpp` | Enable taproot mode |

---

## Usage

```bash
# Grind for Q.x prefix (tweaked output key)
VanitySearch.exe -taproot -tx CAFE42 --prefix 3 -gpu -stop

# Output includes:
# - Private key d
# - Internal key P.x
# - Output key Q.x (matches target)
```

---

## Verification

```python
from ecdsa import SECP256k1, SigningKey
import hashlib

def verify_taproot(privkey_hex, expected_q_prefix):
    # Compute P = d*G
    sk = SigningKey.from_string(bytes.fromhex(privkey_hex), curve=SECP256k1)
    P = sk.get_verifying_key().pubkey.point
    P_x = P.x().to_bytes(32, 'big')

    # Compute t = tagged_hash("TapTweak", P.x)
    tag = b"TapTweak"
    tag_hash = hashlib.sha256(tag).digest()
    t_bytes = hashlib.sha256(tag_hash + tag_hash + P_x).digest()
    t = int.from_bytes(t_bytes, 'big') % SECP256k1.order

    # Compute Q = P + t*G
    G = SECP256k1.generator
    tG = t * G
    Q = P + tG
    Q_x = Q.x().to_bytes(32, 'big').hex().upper()

    # Verify prefix
    assert Q_x.startswith(expected_q_prefix.upper())
    return Q_x
```

---

## Backup

Pre-implementation state saved in branch: `backup/pre-taproot-gpu`
