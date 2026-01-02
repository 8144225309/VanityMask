# VanityMask Test Report - WINDOWS

**Generated**: 2026-01-02 06:15:44
**Platform**: windows
**Executable**: x64\Release\VanitySearch.exe

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 35 |
| Passed | 33 |
| Failed | 2 |
| Pass Rate | 94.3% |
| Total Duration | 3.8 min |

## Hardware Utilization

| Metric | Average | Peak | Target |
|--------|---------|------|--------|
| GPU Util | 44.2% | 100.0% | 90-95% |
| GPU Temp | 51.0C | 65.0C | <85C |
| GPU Power | 225W | 433W | - |

## Test Results

| Test ID | Description | Duration | GPU% | Throughput | Result |
|---------|-------------|----------|------|------------|--------|
| MASK-01 | 32-bit prefix warmup | 3.7s | 18% | N/A | PASS |
| MASK-02 | 40-bit sustained stress | 30.0s | 63% | N/A | PASS |
| MASK-03 | 48-bit max stress | 22.0s | 58% | N/A | PASS |
| MASK-04 | Different 32-bit pattern | 3.2s | 2% | N/A | PASS |
| MASK-05 | Different target pattern | 3.2s | 18% | N/A | PASS |
| SIG-01 | 16-bit ECDSA warmup | 2.1s | 2% | N/A | PASS |
| SIG-02 | 40-bit ECDSA stress | 30.0s | 62% | N/A | PASS |
| SIG-03 | Low-S normalization | 1.6s | 2% | N/A | PASS |
| SIG-04 | Different privkey | 2.1s | 2% | N/A | PASS |
| SCHNORR-01 | 32-bit Schnorr warmup | 3.7s | 17% | N/A | PASS |
| SCHNORR-02 | 40-bit Schnorr stress | 30.0s | 61% | N/A | PASS |
| SCHNORR-03 | Y-parity verification | 2.1s | 2% | N/A | PASS |
| TXID-01 | 16-bit prefix warmup | 2.1s | 2% | N/A | PASS |
| TXID-02 | 24-bit sustained stress | 30.0s | 3% | N/A | PASS |
| TXID-03 | Custom nonce offset | 2.1s | 3% | N/A | PASS |
| VANITY-01 | P2PKH 3-char quick | 1.6s | 3% | N/A | PASS |
| VANITY-02 | Case insensitive | 1.6s | 2% | N/A | PASS |
| VANITY-03 | Bech32 sustained | 22.0s | 80% | N/A | PASS |
| VANITY-04 | Short prefix | 1.6s | 2% | N/A | FAIL |
| TAP-01 | 24-bit Q.x warmup | 7.2s | 61% | 2.12 MKey/s | PASS |
| TAP-02 | 32-bit Taproot stress | 22.0s | 77% | N/A | PASS |
| CPU-01 | CPU mask mode 24-bit | 0.5s | 1% | N/A | PASS |
| CPU-02 | Vanity mode all cores | 0.5s | 1% | N/A | PASS |
| CPU-03 | No SSE mode | 0.5s | 1% | N/A | PASS |
| CPU-04 | Single thread baseline | 0.5s | 1% | N/A | PASS |
| IO-01 | Output to file | 2.1s | 1% | N/A | FAIL |
| IO-02 | Input from file | 2.1s | 1% | N/A | PASS |
| ERR-01 | Invalid prefix char | 0.0s | 4% | N/A | PASS |
| ERR-02 | Missing mask target | 0.0s | 3% | N/A | PASS |
| UTIL-01 | Version check | 0.0s | 5% | N/A | PASS |
| UTIL-02 | Help output | 0.0s | 1% | N/A | PASS |
| UTIL-03 | List GPUs | 0.1s | 2% | N/A | PASS |
| UTIL-04 | Compute address | 0.0s | 1% | N/A | PASS |
| UTIL-05 | Key pair gen | 0.0s | 3% | N/A | PASS |
| UTIL-06 | Compute pubkey | 0.0s | 3% | N/A | PASS |

## Failed Test Details

### VANITY-04: Short prefix

**Command**: `-gpu -stop 1Aa`

**Error**:
```
No error output
```

### IO-01: Output to file

**Command**: `-gpu -stop -o test_output.txt 1Ab`

**Error**:
```
No error output
```

