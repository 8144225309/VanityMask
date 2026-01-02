# VanityMask Test Report - WSL

**Generated**: 2026-01-02 01:25:07
**Platform**: wsl
**Executable**: /mnt/c/pirqjobs/vanitymask-workshop/VanityMask-wsl-test/VanitySearch

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 31 |
| Passed | 27 |
| Failed | 4 |
| Pass Rate | 87.1% |
| Total Duration | 7.4 min |

## Hardware Utilization

| Metric | Average | Peak | Target |
|--------|---------|------|--------|
| GPU Util | 33.5% | 100.0% | 90-95% |
| GPU Temp | 48.3C | 67.0C | <85C |
| GPU Power | 188W | 448W | - |

## Test Results

| Test ID | Description | Duration | GPU% | Throughput | Result |
|---------|-------------|----------|------|------------|--------|
| MASK-01 | 32-bit prefix warmup | 5.9s | 1% | N/A | PASS |
| MASK-02 | 40-bit sustained stress | 30.0s | 87% | N/A | PASS |
| MASK-03 | 48-bit max stress | 22.0s | 88% | N/A | PASS |
| MASK-04 | Different 32-bit pattern | 2.7s | 2% | N/A | PASS |
| MASK-05 | Different target pattern | 2.7s | 5% | N/A | PASS |
| SIG-01 | 16-bit ECDSA warmup | 2.7s | 4% | N/A | PASS |
| SIG-02 | 40-bit ECDSA stress | 30.0s | 89% | N/A | PASS |
| SIG-03 | Low-S normalization | 2.6s | 33% | N/A | PASS |
| SIG-04 | Different privkey | 2.1s | 1% | N/A | PASS |
| SCHNORR-01 | 32-bit Schnorr warmup | 2.6s | 1% | N/A | PASS |
| SCHNORR-02 | 40-bit Schnorr stress | 30.0s | 88% | N/A | PASS |
| SCHNORR-03 | Y-parity verification | 2.2s | 12% | N/A | PASS |
| TXID-01 | 16-bit prefix warmup | 2.1s | 1% | N/A | PASS |
| TXID-02 | 24-bit sustained stress | 30.0s | 7% | N/A | PASS |
| TXID-03 | Custom nonce offset | 2.2s | 3% | N/A | PASS |
| VANITY-01 | P2PKH 3-char quick | 2.2s | 1% | N/A | PASS |
| VANITY-02 | Case insensitive | 2.2s | 1% | N/A | PASS |
| VANITY-03 | Bech32 sustained | 22.0s | 86% | N/A | PASS |
| VANITY-04 | Short prefix | 2.2s | 1% | N/A | PASS |
| TAP-01 | 24-bit Q.x warmup | 13.7s | 78% | 2.56 MKey/s | PASS |
| TAP-02 | 32-bit Taproot stress | 22.0s | 85% | N/A | PASS |
| CPU-01 | Vanity mode all cores | 30.0s | 1% | N/A | FAIL |
| CPU-02 | Vanity multi-thread | 60.0s | 1% | N/A | FAIL |
| CPU-03 | No SSE mode | 60.0s | 1% | N/A | FAIL |
| CPU-04 | Single thread baseline | 60.0s | 0% | N/A | FAIL |
| UTIL-01 | Version check | 0.1s | 0% | N/A | PASS |
| UTIL-02 | Help output | 0.1s | 0% | N/A | PASS |
| UTIL-03 | List GPUs | 0.3s | 0% | N/A | PASS |
| UTIL-04 | Compute address | 0.1s | 0% | N/A | PASS |
| UTIL-05 | Key pair gen | 0.1s | 0% | N/A | PASS |
| UTIL-06 | Compute pubkey | 0.1s | 0% | N/A | PASS |

## Failed Test Details

### CPU-01: Vanity mode all cores

**Command**: `-t 16 -stop 1Te`

**Error**:
```
No error output
```

### CPU-02: Vanity multi-thread

**Command**: `-t 16 -stop 1Ab`

**Error**:
```
No error output
```

### CPU-03: No SSE mode

**Command**: `-nosse -t 8 -stop 1Aa`

**Error**:
```
No error output
```

### CPU-04: Single thread baseline

**Command**: `-t 1 -stop 1A`

**Error**:
```
No error output
```

