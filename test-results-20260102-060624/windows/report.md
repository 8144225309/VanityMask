# VanityMask Test Report - WINDOWS

**Generated**: 2026-01-02 06:11:00
**Platform**: windows
**Executable**: x64\Release\VanitySearch.exe

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 35 |
| Passed | 34 |
| Failed | 1 |
| Pass Rate | 97.1% |
| Total Duration | 4.2 min |

## Hardware Utilization

| Metric | Average | Peak | Target |
|--------|---------|------|--------|
| GPU Util | 51.4% | 97.0% | 90-95% |
| GPU Temp | 49.8C | 64.0C | <85C |
| GPU Power | 248W | 433W | - |

## Test Results

| Test ID | Description | Duration | GPU% | Throughput | Result |
|---------|-------------|----------|------|------------|--------|
| MASK-01 | 32-bit prefix warmup | 4.2s | 17% | N/A | PASS |
| MASK-02 | 40-bit sustained stress | 30.0s | 71% | N/A | PASS |
| MASK-03 | 48-bit max stress | 22.0s | 68% | N/A | PASS |
| MASK-04 | Different 32-bit pattern | 3.6s | 20% | N/A | PASS |
| MASK-05 | Different target pattern | 3.1s | 2% | N/A | PASS |
| SIG-01 | 16-bit ECDSA warmup | 2.1s | 2% | N/A | PASS |
| SIG-02 | 40-bit ECDSA stress | 30.0s | 71% | N/A | PASS |
| SIG-03 | Low-S normalization | 2.1s | 3% | N/A | PASS |
| SIG-04 | Different privkey | 2.1s | 2% | N/A | PASS |
| SCHNORR-01 | 32-bit Schnorr warmup | 3.2s | 2% | N/A | PASS |
| SCHNORR-02 | 40-bit Schnorr stress | 30.0s | 62% | N/A | PASS |
| SCHNORR-03 | Y-parity verification | 1.6s | 2% | N/A | PASS |
| TXID-01 | 16-bit prefix warmup | 2.1s | 2% | N/A | PASS |
| TXID-02 | 24-bit sustained stress | 30.0s | 3% | N/A | PASS |
| TXID-03 | Custom nonce offset | 1.6s | 2% | N/A | PASS |
| VANITY-01 | P2PKH 3-char quick | 1.6s | 2% | N/A | PASS |
| VANITY-02 | Case insensitive | 1.6s | 2% | N/A | PASS |
| VANITY-03 | Bech32 sustained | 22.0s | 79% | N/A | PASS |
| VANITY-04 | Short prefix | 1.6s | 2% | N/A | PASS |
| TAP-01 | 24-bit Q.x warmup | 31.0s | 79% | 2.14 MKey/s | PASS |
| TAP-02 | 32-bit Taproot stress | 22.0s | 77% | N/A | PASS |
| CPU-01 | CPU mask mode 24-bit | 0.5s | 2% | N/A | PASS |
| CPU-02 | Vanity mode all cores | 0.5s | 2% | N/A | PASS |
| CPU-03 | No SSE mode | 0.5s | 3% | N/A | PASS |
| CPU-04 | Single thread baseline | 0.5s | 3% | N/A | PASS |
| IO-01 | Output to file | 0.0s | 2% | N/A | FAIL |
| IO-02 | Input from file | 1.6s | 2% | N/A | PASS |
| ERR-01 | Invalid prefix char | 0.0s | 2% | N/A | PASS |
| ERR-02 | Missing mask target | 0.0s | 2% | N/A | PASS |
| UTIL-01 | Version check | 0.0s | 2% | N/A | PASS |
| UTIL-02 | Help output | 0.0s | 2% | N/A | PASS |
| UTIL-03 | List GPUs | 0.1s | 3% | N/A | PASS |
| UTIL-04 | Compute address | 0.0s | 2% | N/A | PASS |
| UTIL-05 | Key pair gen | 0.0s | 3% | N/A | PASS |
| UTIL-06 | Compute pubkey | 0.0s | 3% | N/A | PASS |

## Failed Test Details

### IO-01: Output to file

**Command**: `-gpu -stop 1Ab -o test_output.txt`

**Error**:
```
No error output
```

