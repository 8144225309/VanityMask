# VanityMask Comprehensive Test Plan

**Version:** 1.0
**Date:** 2026-01-01
**GPU:** NVIDIA GeForce RTX 4090

## Test Categories

### 1. Validity Tests
Verify that each mode produces cryptographically correct results.

| Mode | Test | Verification Method |
|------|------|---------------------|
| MASK | 8/16/24/32-bit prefix | PubKey.x starts with target |
| SIG-ECDSA | 8/16/32-bit prefix | R.x starts with target, signature valid |
| SIG-SCHNORR | 8/16/32-bit prefix | R.x starts with target, BIP-340 valid |
| TAPROOT | 8/12/16-bit prefix | Q.x starts with target after tweak |
| TXID | 8/16-bit prefix | TXID starts with target after double-SHA256 |

### 2. Performance Benchmarks
Measure throughput and GPU utilization for each mode.

| Mode | Expected Throughput | GPU Utilization Target |
|------|--------------------|-----------------------|
| MASK | ~8.5 GKeys/s | >80% |
| SIG-ECDSA | ~8.5 GKeys/s | >80% |
| SIG-SCHNORR | ~8.5 GKeys/s | >80% |
| TAPROOT | ~1.0 GKeys/s | >70% |
| TXID | ~10 MKeys/s | >50% |

### 3. Edge Cases
Test boundary conditions and error handling.

- Invalid hex input
- Empty target
- Target longer than 64 chars
- Missing required parameters

### 4. Kernel Variance Tests
Test different bit depths to ensure kernel scaling.

| Mode | Bit Depths |
|------|-----------|
| MASK | 8, 16, 24, 32, 40, 48 |
| SIG | 8, 16, 24, 32 |
| TAPROOT | 8, 12, 16, 20 |
| TXID | 8, 16, 24 |

## Test Execution

```bash
# Full test suite with benchmarks
python comprehensive_test_suite.py --full --benchmark

# Quick validity check
python comprehensive_test_suite.py --quick
```

## Success Criteria

1. **Validity**: 100% of tests pass verification
2. **Performance**: Throughput within 10% of baseline
3. **GPU Utilization**: Average >50% across all modes
4. **Stability**: No crashes, hangs, or memory leaks
