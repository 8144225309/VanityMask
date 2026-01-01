# MASK/SIG Mode Key Reconstruction Bug Fix

**Date:** 2026-01-01
**Status:** Fixed and Verified

## Problem Summary

The MASK and SIG (ECDSA/Schnorr) modes were finding matches but reconstructing incorrect private keys. The GPU correctly identified points where X coordinates matched the target prefix, but the CPU-side key reconstruction produced wrong keys.

### Symptoms
- MASK mode: Output PubKey.x didn't start with target prefix
- SIG modes: Output R.x didn't start with target prefix
- Verification: 0/4 MASK verified, 0/3 SCHNORR verified (before fix)

## Root Cause Analysis

### Issue 1: Incorrect centerOffset Formula

The original code in `Vanity.cpp` lines 1809-1816:
```cpp
int32_t centerOffset = groupSize / 2;   // 512
int32_t actualOffset = it.incr - centerOffset;  // WRONG!
if (actualOffset >= 0) {
    finalKey.Add((uint64_t)actualOffset);
} else {
    finalKey.Sub((uint64_t)(-actualOffset));
}
```

This subtracted 512 from the incr value, but the GPU's incr values (0-1023) directly map to key offsets without needing this subtraction.

### Issue 2: GPU Pipeline Timing Offset

The more subtle issue was in the GPU result processing timing:

```
GPU Pipeline Structure:
┌─────────────────────────────────────────────────────────────┐
│ LaunchStego() does TWO things:                              │
│   1. Returns results from PREVIOUS kernel                   │
│   2. Starts the NEXT kernel                                 │
└─────────────────────────────────────────────────────────────┘

Main Loop Timing:
┌─────────────────────────────────────────────────────────────┐
│ Iteration 0:                                                │
│   - LaunchStego #0: returns 0 results, starts kernel #0     │
│   - Process 0 results                                       │
│   - Update keys: keys += STEP_SIZE (1024)                   │
│                                                             │
│ Iteration 1:                                                │
│   - LaunchStego #1: returns kernel #0 results               │
│   - Process kernel #0 results                               │
│     └── BUT keys = original + STEP_SIZE (already updated!)  │
│   - Update keys: keys += STEP_SIZE                          │
└─────────────────────────────────────────────────────────────┘
```

When processing kernel #0 results, the CPU keys have already been advanced by `STEP_SIZE`. This requires compensation in the reconstruction formula.

## The Fix

### Correct Formula

For a GPU match at `incr=I`:
- GPU matched key: `original_keys + I`
- CPU keys at processing time: `original_keys + STEP_SIZE`
- Therefore: `finalKey = keys + incr - STEP_SIZE`

Since `STEP_SIZE = groupSize = 1024`:
```cpp
finalKey = keys[thId] + incr - groupSize
```

### Code Change

**File:** `Vanity.cpp`
**Lines:** 1805-1818

**Before (broken):**
```cpp
} else {
  int32_t groupSize = g.GetGroupSize();
  int32_t centerOffset = groupSize / 2;
  int32_t actualOffset = it.incr - centerOffset;
  if (actualOffset >= 0) {
    finalKey.Add((uint64_t)actualOffset);
  } else {
    finalKey.Sub((uint64_t)(-actualOffset));
  }
}
```

**After (fixed):**
```cpp
} else {
  // Step 1: Compute key from incr
  // GPU incr maps to: matched_key = original_keys + incr
  // But results are processed after keys updated by STEP_SIZE (=groupSize)
  // So: finalKey = keys + incr - STEP_SIZE = keys + incr - groupSize
  int32_t groupSize = g.GetGroupSize();
  if (it.incr >= 0) {
    finalKey.Add((uint64_t)it.incr);
  } else {
    finalKey.Sub((uint64_t)(-it.incr));
  }
  // Account for timing: results from previous kernel, keys already advanced
  finalKey.Sub((uint64_t)groupSize);
}
```

## Verification Results

### Before Fix
```
Total tests: 17
Passed: 16 (94.1%)
Verified: 10 (58.8%)

By Mode:
  mask: 6/6 passed, 2/6 verified      ❌
  sig-ecdsa: 3/3 passed, 3/3 verified ✓ (false positive - only checked math)
  sig-schnorr: 2/3 passed, 0/3 verified ❌
  txid: 3/3 passed, 3/3 verified      ✓
```

### After Fix
```
Total tests: 17
Passed: 17 (100.0%)
Verified: 17 (100.0%)

By Mode:
  mask: 6/6 passed, 6/6 verified       ✓
  sig-ecdsa: 3/3 passed, 3/3 verified  ✓
  sig-schnorr: 3/3 passed, 3/3 verified ✓
  txid: 3/3 passed, 3/3 verified       ✓
```

## Technical Details

### GPU Kernel incr Values

The stego kernel (`GPUCompute.h` lines 604-654) stores incr values as:
- `j*GRP_SIZE + (GRP_SIZE/2)` for center point (incr=512 for j=0)
- `j*GRP_SIZE + (GRP_SIZE/2 + (i+1))` for positive offsets
- `j*GRP_SIZE + (GRP_SIZE/2 - (i+1))` for negative offsets
- `j*GRP_SIZE + 0` for first point (incr=0 for j=0)

These incr values (0-1023) directly correspond to key offsets from `keys[thId]`.

### GPU Starting Point Setup

In `getGPUStartingKeys()`:
```cpp
k.Add((uint64_t)(groupSize / 2));  // Add 512
p[i] = secp->ComputePublicKey(&k);
```

The GPU receives `p[i] = (keys[i] + 512) * G` as its starting point. The kernel then iterates from this center, checking points at offsets -512 to +511.

### Key Relationship

```
GPU starting point for thread i: (keys[i] + 512) * G
GPU incr=0:    keys[i] * G
GPU incr=512:  (keys[i] + 512) * G  (center)
GPU incr=1023: (keys[i] + 1023) * G
```

## Files Modified

| File | Change |
|------|--------|
| `Vanity.cpp` | Fixed key reconstruction formula (lines 1805-1818) |

## Testing Commands

```bash
# Quick verification test
python tests/comprehensive_test_suite.py --quick

# Manual mask test
./x64/Release/VanitySearch.exe -mask -tx 00 --prefix 1 -stop -gpu
```

## Lessons Learned

1. GPU pipeline timing matters - results may be processed asynchronously
2. Debug output showing intermediate values was crucial for diagnosis
3. The "centerOffset" subtraction was a red herring - the real issue was timing
4. Always verify cryptographic outputs, not just that matches are found
