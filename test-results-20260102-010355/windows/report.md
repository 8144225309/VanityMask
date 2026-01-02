# VanityMask Test Report - WINDOWS

**Generated**: 2026-01-02 01:17:22
**Platform**: windows
**Executable**: VanityMask-windows-test\x64\Release\VanitySearch.exe

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 31 |
| Passed | 31 |
| Failed | 0 |
| Pass Rate | 100.0% |
| Total Duration | 13.1 min |

## Hardware Utilization

| Metric | Average | Peak | Target |
|--------|---------|------|--------|
| GPU Util | 57.6% | 100.0% | 90-95% |
| GPU Temp | 55.5C | 69.0C | <85C |
| GPU Power | 279W | 449W | - |

## Test Results

| Test ID | Description | Duration | GPU% | Throughput | Result |
|---------|-------------|----------|------|------------|--------|
| MASK-01 | 32-bit prefix warmup | 4.2s | 18% | N/A | PASS |
| MASK-02 | 40-bit sustained stress | 120.0s | 68% | N/A | PASS |
| MASK-03 | 48-bit max stress | 90.0s | 67% | N/A | PASS |
| MASK-04 | Different 32-bit pattern | 3.1s | 1% | N/A | PASS |
| MASK-05 | Different target pattern | 3.2s | 1% | N/A | PASS |
| SIG-01 | 16-bit ECDSA warmup | 2.7s | 1% | N/A | PASS |
| SIG-02 | 40-bit ECDSA stress | 120.0s | 70% | N/A | PASS |
| SIG-03 | Low-S normalization | 2.7s | 1% | N/A | PASS |
| SIG-04 | Different privkey | 2.7s | 1% | N/A | PASS |
| SCHNORR-01 | 32-bit Schnorr warmup | 3.2s | 1% | N/A | PASS |
| SCHNORR-02 | 40-bit Schnorr stress | 120.0s | 66% | N/A | PASS |
| SCHNORR-03 | Y-parity verification | 2.6s | 0% | N/A | PASS |
| TXID-01 | 16-bit prefix warmup | 1.6s | 1% | N/A | PASS |
| TXID-02 | 24-bit sustained stress | 120.0s | 2% | N/A | PASS |
| TXID-03 | Custom nonce offset | 2.1s | 1% | N/A | PASS |
| VANITY-01 | P2PKH 3-char quick | 1.6s | 1% | N/A | PASS |
| VANITY-02 | Case insensitive | 1.6s | 1% | N/A | PASS |
| VANITY-03 | Bech32 sustained | 90.0s | 88% | N/A | PASS |
| VANITY-04 | Short prefix | 1.6s | 1% | N/A | PASS |
| TAP-01 | 24-bit Q.x warmup | 2.1s | 1% | N/A | PASS |
| TAP-02 | 32-bit Taproot stress | 90.0s | 83% | N/A | PASS |
| CPU-01 | Vanity mode all cores | 0.5s | 0% | N/A | PASS |
| CPU-02 | Vanity multi-thread | 0.5s | 2% | N/A | PASS |
| CPU-03 | No SSE mode | 0.5s | 1% | N/A | PASS |
| CPU-04 | Single thread baseline | 0.5s | 1% | N/A | PASS |
| UTIL-01 | Version check | 0.0s | 1% | N/A | PASS |
| UTIL-02 | Help output | 0.0s | 1% | N/A | PASS |
| UTIL-03 | List GPUs | 0.1s | 1% | N/A | PASS |
| UTIL-04 | Compute address | 0.0s | 1% | N/A | PASS |
| UTIL-05 | Key pair gen | 0.0s | 1% | N/A | PASS |
| UTIL-06 | Compute pubkey | 0.0s | 1% | N/A | PASS |
