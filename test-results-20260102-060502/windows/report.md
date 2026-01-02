# VanityMask Test Report - WINDOWS

**Generated**: 2026-01-02 06:05:39
**Platform**: windows
**Executable**: VanityMask-windows-test\x64\Release\VanitySearch.exe

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 35 |
| Passed | 0 |
| Failed | 35 |
| Pass Rate | 0.0% |
| Total Duration | 0.0 min |

## Hardware Utilization

| Metric | Average | Peak | Target |
|--------|---------|------|--------|
| GPU Util | 1.4% | 4.0% | 90-95% |
| GPU Temp | 32.0C | 32.0C | <85C |
| GPU Power | 72W | 72W | - |

## Test Results

| Test ID | Description | Duration | GPU% | Throughput | Result |
|---------|-------------|----------|------|------------|--------|
| MASK-01 | 32-bit prefix warmup | 0.0s | 0% | N/A | FAIL |
| MASK-02 | 40-bit sustained stress | 0.0s | 2% | N/A | FAIL |
| MASK-03 | 48-bit max stress | 0.0s | 1% | N/A | FAIL |
| MASK-04 | Different 32-bit pattern | 0.0s | 1% | N/A | FAIL |
| MASK-05 | Different target pattern | 0.0s | 1% | N/A | FAIL |
| SIG-01 | 16-bit ECDSA warmup | 0.0s | 1% | N/A | FAIL |
| SIG-02 | 40-bit ECDSA stress | 0.0s | 1% | N/A | FAIL |
| SIG-03 | Low-S normalization | 0.0s | 1% | N/A | FAIL |
| SIG-04 | Different privkey | 0.0s | 1% | N/A | FAIL |
| SCHNORR-01 | 32-bit Schnorr warmup | 0.0s | 1% | N/A | FAIL |
| SCHNORR-02 | 40-bit Schnorr stress | 0.0s | 2% | N/A | FAIL |
| SCHNORR-03 | Y-parity verification | 0.0s | 1% | N/A | FAIL |
| TXID-01 | 16-bit prefix warmup | 0.0s | 2% | N/A | FAIL |
| TXID-02 | 24-bit sustained stress | 0.0s | 1% | N/A | FAIL |
| TXID-03 | Custom nonce offset | 0.0s | 1% | N/A | FAIL |
| VANITY-01 | P2PKH 3-char quick | 0.0s | 2% | N/A | FAIL |
| VANITY-02 | Case insensitive | 0.0s | 1% | N/A | FAIL |
| VANITY-03 | Bech32 sustained | 0.0s | 1% | N/A | FAIL |
| VANITY-04 | Short prefix | 0.0s | 1% | N/A | FAIL |
| TAP-01 | 24-bit Q.x warmup | 0.0s | 2% | N/A | FAIL |
| TAP-02 | 32-bit Taproot stress | 0.0s | 1% | N/A | FAIL |
| CPU-01 | CPU mask mode 24-bit | 0.0s | 1% | N/A | FAIL |
| CPU-02 | Vanity mode all cores | 0.0s | 1% | N/A | FAIL |
| CPU-03 | No SSE mode | 0.0s | 1% | N/A | FAIL |
| CPU-04 | Single thread baseline | 0.0s | 1% | N/A | FAIL |
| IO-01 | Output to file | 0.0s | 1% | N/A | FAIL |
| IO-02 | Input from file | 0.0s | 3% | N/A | FAIL |
| ERR-01 | Invalid prefix char | 0.0s | 1% | N/A | FAIL |
| ERR-02 | Missing mask target | 0.0s | 4% | N/A | FAIL |
| UTIL-01 | Version check | 0.0s | 1% | N/A | FAIL |
| UTIL-02 | Help output | 0.0s | 2% | N/A | FAIL |
| UTIL-03 | List GPUs | 0.0s | 1% | N/A | FAIL |
| UTIL-04 | Compute address | 0.0s | 1% | N/A | FAIL |
| UTIL-05 | Key pair gen | 0.0s | 4% | N/A | FAIL |
| UTIL-06 | Compute pubkey | 0.0s | 2% | N/A | FAIL |

## Failed Test Details

### MASK-01: 32-bit prefix warmup

**Command**: `-gpu -mask -tx DEADBEEF --prefix 4 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### MASK-02: 40-bit sustained stress

**Command**: `-gpu -mask -tx DEADBEEFAA --prefix 5`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### MASK-03: 48-bit max stress

**Command**: `-gpu -mask -tx DEADBEEFAABB --prefix 6`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### MASK-04: Different 32-bit pattern

**Command**: `-gpu -mask -tx BABECAFE --prefix 4 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### MASK-05: Different target pattern

**Command**: `-gpu -mask -tx CAFEBABE --prefix 4 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### SIG-01: 16-bit ECDSA warmup

**Command**: `-gpu -sig -tx DEAD --prefix 2 -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 -d 0000000000000000000000000000000000000000000000000000000000000001 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### SIG-02: 40-bit ECDSA stress

**Command**: `-gpu -sig -tx DEADBEEFAA --prefix 5 -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 -d 0000000000000000000000000000000000000000000000000000000000000001`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### SIG-03: Low-S normalization

**Command**: `-gpu -sig -tx AAAA --prefix 2 -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 -d 0000000000000000000000000000000000000000000000000000000000000001 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### SIG-04: Different privkey

**Command**: `-gpu -sig -tx BBBB --prefix 2 -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 -d aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### SCHNORR-01: 32-bit Schnorr warmup

**Command**: `-gpu -sig -tx DEADBEEF --prefix 4 -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 -d 0000000000000000000000000000000000000000000000000000000000000001 --schnorr -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### SCHNORR-02: 40-bit Schnorr stress

**Command**: `-gpu -sig -tx DEADBEEFAA --prefix 5 -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 -d 0000000000000000000000000000000000000000000000000000000000000001 --schnorr`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### SCHNORR-03: Y-parity verification

**Command**: `-gpu -sig -tx CAFE --prefix 2 -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 -d 0000000000000000000000000000000000000000000000000000000000000001 --schnorr -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### TXID-01: 16-bit prefix warmup

**Command**: `-gpu -txid -raw 010000000100000000000000000000000000000000000000000000000000000000000000000000000000ffffffff0100000000000000000000000000 -tx DEAD --prefix 2 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### TXID-02: 24-bit sustained stress

**Command**: `-gpu -txid -raw 010000000100000000000000000000000000000000000000000000000000000000000000000000000000ffffffff0100000000000000000000000000 -tx DEADBE --prefix 3`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### TXID-03: Custom nonce offset

**Command**: `-gpu -txid -raw 010000000100000000000000000000000000000000000000000000000000000000000000000000000000ffffffff0100000000000000000000000000 -tx CAFE --prefix 2 -nonce-offset 10 -nonce-len 4 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### VANITY-01: P2PKH 3-char quick

**Command**: `-gpu -stop 1Te`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### VANITY-02: Case insensitive

**Command**: `-gpu -c -stop 1drew`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### VANITY-03: Bech32 sustained

**Command**: `-gpu bc1qtest`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### VANITY-04: Short prefix

**Command**: `-gpu -stop 1Aa`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### TAP-01: 24-bit Q.x warmup

**Command**: `-gpu -taproot -tx DEADBE --prefix 3 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### TAP-02: 32-bit Taproot stress

**Command**: `-gpu -taproot -tx DEADBEEF --prefix 4`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### CPU-01: CPU mask mode 24-bit

**Command**: `-t 8 -mask -tx ABCDEF --prefix 3 -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### CPU-02: Vanity mode all cores

**Command**: `-t 16 -stop 1Te`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### CPU-03: No SSE mode

**Command**: `-nosse -t 8 -stop 1Aa`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### CPU-04: Single thread baseline

**Command**: `-t 1 -stop 1A`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### IO-01: Output to file

**Command**: `-gpu -stop 1Ab -o test_output.txt`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### IO-02: Input from file

**Command**: `-gpu -stop -i test_input.txt`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### ERR-01: Invalid prefix char

**Command**: `-stop 1Invalid0OIl`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### ERR-02: Missing mask target

**Command**: `-mask -stop`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### UTIL-01: Version check

**Command**: `-v`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### UTIL-02: Help output

**Command**: `-h`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### UTIL-03: List GPUs

**Command**: `-l`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### UTIL-04: Compute address

**Command**: `-ca 0479BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### UTIL-05: Key pair gen

**Command**: `-s AStrongTestSeedPassphrase1234567890 -kp`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

### UTIL-06: Compute pubkey

**Command**: `-cp 0000000000000000000000000000000000000000000000000000000000000001`

**Error**:
```
[WinError 2] The system cannot find the file specified
```

