# Taproot GPU Mode Fix

## Overview

This document describes the fix for the taproot post-tweak grinding mode in VanitySearch. The mode allows grinding for Bitcoin taproot addresses where the tweaked output key Q.x matches a target prefix.

## Background: Taproot Key Derivation

In BIP-340/341 (Taproot), the output public key Q is derived from an internal key P:

```
Q = P + hash("TapTweak", P.x) * G
```

Where:
- P = d * G (internal public key from private key d)
- hash("TapTweak", P.x) = SHA256(SHA256("TapTweak") || SHA256("TapTweak") || P.x)
- G = secp256k1 generator point

The taproot grinding mode searches for private keys `d` such that Q.x starts with a desired prefix (e.g., `0000...` for vanity addresses).

## The Bug

### Symptom
GPU would find matches (Q.x with correct prefix), but the CPU's reconstructed private key produced a **different P.x** than what the GPU found. This caused verification to fail.

### Root Cause
The `SetKeys()` function in `GPU/GPUEngine.cu` was calling `callKernel()` at the end:

```cpp
// OLD CODE (BUGGY)
bool GPUEngine::SetKeys(Point *p) {
  // ... copy points to GPU memory ...
  return callKernel();  // <-- THIS WAS THE BUG
}
```

`callKernel()` launches the **standard vanity search kernel**, which:
1. Reads the input points
2. **Modifies them** (increments by group offsets)
3. Stores results

When taproot mode subsequently called `LaunchTaproot()`, the GPU memory was already corrupted by the standard kernel. The taproot kernel was working on different points than the CPU expected.

### Timeline of Bug
```
1. CPU: SetKeys(p[]) - copies points to GPU
2. GPU: callKernel() - CORRUPTS the points by running standard vanity kernel
3. CPU: LaunchTaproot() - launches taproot kernel
4. GPU: comp_keys_taproot() - works on WRONG points
5. GPU: Finds match, stores P.x and Q.x
6. CPU: Reconstructs key from keys[tid] - gets DIFFERENT P.x
```

## The Fix

### GPUEngine.cu (lines 711-720)

```cpp
// NEW CODE (FIXED)
bool GPUEngine::SetKeys(Point *p) {
  // ... copy points to GPU memory ...
  cudaError_t err = cudaGetLastError();
  if (err != cudaSuccess) {
    printf("GPUEngine: SetKeys: %s\n", cudaGetErrorString(err));
    return false;
  }

  // Don't call any kernel here - let the caller decide which kernel to launch
  // The old code called callKernel() which would run the standard vanity kernel
  // and corrupt the data for taproot/stego modes.
  return true;
}
```

### GPUHash.h (lines 279-295)

Fixed byte order in `SHA256_TapTweak()`. Removed incorrect `bswap32()` calls:

```cpp
// OLD CODE (INCORRECT)
w[0] = bswap32((uint32_t)(px[3] >> 32));  // Wrong!

// NEW CODE (CORRECT)
w[0] = (uint32_t)(px[3] >> 32);  // No bswap needed
```

The `px[]` array stores **numeric values**, not byte arrays. When we extract bits with `px[3] >> 32`, we get the correct numeric value that SHA256 expects. Adding `bswap32()` incorrectly reversed the bytes.

## Verification

The fix was verified using Python to independently compute the taproot derivation:

```python
# Test output from VanitySearch
d = 0xA4210AD32FEA0A8C1D8B11F63886A835FE5D0C00BAC883E7FFBA9C876C00D2EC

# Compute P = d * G
P = d * G
P_x = 0x07F8E71C186B8D1F53A359616A24EA12786DABCFB5E8AE8F869F7A7DA1D6BA12

# Compute t = TapTweak(P.x)
t = 0x420CC26C88E05B25839136FFCE9F1654E618C7BDEA2DCF191FF0448B39966B4D

# Compute Q = P + t*G
Q_x = 0x0000D140683EF1D89950C8A010298F04038556BD78C076C102DC7B6CBC2B92EA

# SUCCESS: Q.x starts with 0000 (matches 16-bit prefix)
```

## Files Changed

| File | Change |
|------|--------|
| `GPU/GPUEngine.cu` | Fixed SetKeys() to not call callKernel() |
| `GPU/GPUHash.h` | Removed incorrect bswap32() from SHA256_TapTweak() |
| `Vanity.cpp` | Removed debug output |

## Test Scripts

Python verification scripts are in `tests/`:
- `verify_final.py` - Verifies a found key produces correct Q.x
- `verify_gpu_values.py` - Compares GPU intermediate values with Python
- `verify_taproot_key.py` - Full taproot key verification

## Usage

```bash
# Find taproot address with Q.x starting with 0000 (16 bits)
VanitySearch.exe -taproot -tx 0000 --prefix 2 -gpu -stop

# Find taproot address with Q.x starting with DEAD (16 bits)
VanitySearch.exe -taproot -tx DEAD --prefix 2 -gpu -stop
```

## Performance Note

Taproot mode is ~50-100x slower than standard mask mode because each candidate requires:
1. SHA256 tagged hash computation
2. Scalar multiplication (t * G)
3. Point addition (P + tG)

This is unavoidable due to the taproot key derivation formula.
