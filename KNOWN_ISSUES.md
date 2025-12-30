# VanityMask Known Issues & Behavior Log

## Status Summary

| Mode | Status | Notes |
|------|--------|-------|
| TXID (-txid) | Working | Verified with Python |
| Mask (-mask) | Working | Verified with Python (ecdsa) |
| Signature (-sig) | Working | s-value bug FIXED 2024-12-30 |

---

## Issues & Behaviors

### 1. TXID Mode: 62% GPU Utilization (Expected Behavior)

**Observed**: GPU utilization ~62% in TXID mode vs ~100% in original VanitySearch

**Root Cause**: Memory-bound kernel design
- TXID kernel allocates `uint8_t tx[4096]` per thread (4KB)
- RTX 4090 has only 1KB registers per thread
- Causes register spilling to L1 cache/global memory
- GPU cores idle waiting on memory operations

**Impact**: ~10 Mkey/s throughput (vs ~8 GKeys/s for EC operations)

**Status**: Working as designed. Could be optimized with SHA256 midstate precomputation (2-4x improvement potential).

---

### 2. TXID Mode: CPU Thread Counter Inflation (FIXED)

**Observed**: TXID-32 benchmarks showed 2^37+ attempts without finding match

**Root Cause**: CPU threads were running standard EC key searches (not TXID grinding) but their work was counted in "Total" counter, inflating it ~100x.

**Fix Applied**: Disabled CPU threads in TXID mode (`Vanity.cpp` line 1938)
```cpp
if (txidMode) {
    nbCPUThread = 0;
}
```

**Status**: FIXED - Verified 2024-12-30

---

### 3. TXID Mode: SHA256 Second Pass Bug (FIXED)

**Observed**: GPU computed different TXID than Python verification

**Root Cause**: Incorrect `bswap32()` applied between first and second SHA256 passes in `GPU/GPUEngine.cu` lines 175-186.

**Fix Applied**: Removed bswap32, pass s1[] directly to second SHA256 pass.

**Status**: FIXED - Verified with Python 2024-12-30

---

### 4. Signature Mode: s-value Bug (FIXED)

**Observed**: Signature mode produced incorrect s-values

**Root Cause**: In `Vanity.cpp` `ModInvOrder()` function, `temp.Mult(&x2)` used regular multiplication. When multiplying two 256-bit numbers (q and x2), the result needs 512 bits but overflowed, causing garbage.

**Fix Applied**: Changed `temp.Mult(&x2)` to `temp.ModMulK1order(&x2)` to use modular multiplication. Also replaced the subtraction logic with `ModSubK1order()`.

**Location**: `Vanity.cpp` lines 43-86, function `ModInvOrder()`

**Verification**:
```
R.x computed:  DEADC25CCFCFBADD96D3E311B1517D2923979FB83A085E255396AA22730FF758
R.x from GPU:  DEADC25CCFCFBADD96D3E311B1517D2923979FB83A085E255396AA22730FF758
R.x match: True

s computed:    4AEA77E90EF8B6380C4E18B5BED02FA9BFFFBE7FC2D8E9BCC23B54ECC979B599
s from GPU:    4AEA77E90EF8B6380C4E18B5BED02FA9BFFFBE7FC2D8E9BCC23B54ECC979B599
s match: True
```

**Status**: FIXED - Verified 2024-12-30

---

## Test Results Log

### TXID Mode Tests (2024-12-30)

| Test | Prefix | Difficulty | Result | Verified |
|------|--------|------------|--------|----------|
| TXID-8 | `de` | 2^8 | PASS | Python |
| TXID-16 | `dead` | 2^16 | PASS | Python |
| TXID-24 | `dead00` | 2^24 | PASS | Python |
| TXID-24 | `cafe42` | 2^24 | PASS | Python |
| TXID-32 | `abcd1234` | 2^32 | PASS | Python |
| TXID-32 | `12345678` | 2^32 | PASS | Python |

### Mask Mode Tests (2024-12-30)

| Test | Prefix | Difficulty | Result | Verified |
|------|--------|------------|--------|----------|
| Mask-16 | `dead` | 2^16 | PASS | Python (ecdsa) |
| Mask-24 | `deadbe` | 2^24 | PASS | Python (ecdsa) |

### Signature Mode Tests (2024-12-30)

| Test | Prefix | Difficulty | R.x | s-value | Result |
|------|--------|------------|-----|---------|--------|
| Sig-16 | `dead` | 2^16 | PASS | PASS | **FIXED** |

---

## Performance Benchmarks

### TXID Mode (RTX 4090)
- GPU Rate: 8-14 Mkey/s (fluctuates with thermal throttling)
- GPU Utilization: ~62%
- Bottleneck: Memory bandwidth (4KB buffer per thread)
- TXID-32 typical time: 5-10 minutes

### Mask Mode (RTX 4090)
- GPU Rate: ~8 GKeys/s
- GPU Utilization: ~100%
- Bottleneck: Compute (EC point operations)
- Very fast for typical prefixes

### Signature Mode (RTX 4090)
- GPU Rate: ~8 GKeys/s
- GPU Utilization: ~100%
- Bottleneck: Compute (EC point operations)
- Same kernel as Mask mode

---

## Notes

### Background Process Behavior
Running VanitySearch in background mode (with stdin redirected from /dev/null) may cause segfaults on Windows due to console I/O handling. Always run interactively or redirect output properly.

### GPU Thermal Behavior
The RTX 4090 rate fluctuates between 8-14 Mkey/s in TXID mode based on thermal conditions. This is normal - the GPU throttles to maintain safe temperatures.
