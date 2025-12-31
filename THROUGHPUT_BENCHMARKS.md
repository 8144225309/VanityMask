# VanityMask Throughput Benchmarks

Benchmarks for steganographic data encoding using VanityMask on RTX 4090.

---

## Hardware Configuration

- **GPU:** NVIDIA GeForce RTX 4090
- **CUDA Cores:** 16,384
- **Memory:** 24GB GDDR6X
- **Driver:** Latest
- **OS:** Windows 10/11

---

## Observed Performance

### Grinding Rates

| Mode | Rate | Notes |
|------|------|-------|
| Mask (-mask) | ~27 GKeys/s | EC point multiplication |
| Signature (-sig) | ~27 GKeys/s | Same kernel as mask |
| TXID (-txid) | ~10 MKeys/s | Double SHA256, memory-bound |

### Startup Overhead

Each grind operation has ~2.5s startup overhead for GPU initialization.

---

## Bit Depth vs Time

### Mask/Signature Mode (27 GKeys/s)

| Bits | Hex Chars | Expected | 99th Percentile | Notes |
|------|-----------|----------|-----------------|-------|
| 16 | 4 | <0.1s | <0.1s | Instant |
| 24 | 6 | <0.1s | <0.1s | Instant |
| 32 | 8 | ~2.7s | ~3.2s | With startup |
| 36 | 9 | ~5s | ~14s | |
| 40 | 10 | ~43s | ~3.2 min | Target depth |
| 44 | 11 | ~11 min | ~50 min | |
| 48 | 12 | ~2.9 hrs | ~13 hrs | |

### TXID Mode (10 MKeys/s)

| Bits | Hex Chars | Expected | 99th Percentile |
|------|-----------|----------|-----------------|
| 16 | 4 | <0.1s | <0.1s |
| 24 | 6 | ~4s | ~10s |
| 28 | 7 | ~27s | ~2 min |
| 32 | 8 | ~7 min | ~32 min |

---

## Benchmark Results

### 40-bit Mask Mode (5 trials)

```
Trial 1: 197.1s (unlucky)
Trial 2: 92.7s
Trial 3: 21.9s (lucky)
Trial 4: 37.6s
Trial 5: >600s (timeout, ~1% expected)

Median: 92.7s
Success rate: 4/5 within 10 min
```

### 32-bit Mask Mode (10 trials)

```
Times: 2.6s, 3.1s, 3.1s, 3.2s, 3.2s, 3.7s, 3.7s, 4.1s, 4.2s, 4.7s
Min: 2.6s, Median: 3.4s, Max: 4.7s
All verified: 10/10
```

### 32-bit Signature Mode (5 trials)

```
Times: 2.7s, 3.1s, 3.2s, 3.7s, 4.2s
All verified: 5/5
```

### 24-bit TXID Mode (5 trials)

```
Times: 2.1s, 4.2s, 4.7s, 4.7s, 5.2s
Median: 4.7s
```

---

## Multi-Channel Throughput

### Per 10-Minute Block

Using 3-minute budget per channel with 99% reliability:

| Configuration | Channels | Bits | Bytes |
|---------------|----------|------|-------|
| Pubkey X only | 1 | 40 | 5 |
| Pubkey + Signature | 2 | 80 | 10 |
| Pubkey + Sig + TXID | 3 | 108 | 13.5 |

### Daily Throughput (144 blocks)

| Reliability | Bits/day | Bytes/day |
|-------------|----------|-----------|
| 99% | 15,552 | 1,944 |
| 95% | 16,704 | 2,088 |

**Conservative estimate: ~1.9 KB/day**

---

## Regtest Verification

### Multi-Block Simulation (3 blocks, 32-bit each)

```
Block 1: pubkey=0B59B9D0, sig=7A7817CE, time=6.8s
Block 2: pubkey=EBAF36B5, sig=87532C35, time=5.8s
Block 3: pubkey=5291B4AD, sig=AAF5796C, time=9.8s

Total: 192 bits (24 bytes) in 22.4s
Average: 7.5s per block
```

### Verified On-Chain

All test transactions successfully:
- Accepted by regtest mempool
- Mined into blocks
- Pubkey data visible in witness when spent
- Signature R.x verified via ECDSA

---

## Recommended Configuration

### For 10-Minute Block Production

| Channel | Bit Depth | Time Budget | Reliability |
|---------|-----------|-------------|-------------|
| Pubkey X | 40 | 3 min | 99% |
| Signature R.x | 40 | 3 min | 99% |
| TXID | 28 | 3 min | 99% |
| **Total** | **108** | **9 min** | **~97%** |

### Fallback Strategy

If a grind exceeds budget:
1. Reduce bit depth by 4 (16x faster)
2. Retry with new random target
3. Accept partial encoding for this block

---

## Comparison to Original Obscurity

| Metric | Original | VanityMask |
|--------|----------|------------|
| GPU optimization | Basic | Highly optimized |
| Throughput | ~100 bytes/day | ~1.9 KB/day |
| Multi-channel | Single | Pubkey + Sig + TXID |
| Regtest verified | No | Yes |

---

## Test Commands

### Quick Verification (32-bit)

```bash
# Pubkey grinding
VanitySearch.exe -mask -tx DEADBEEF --prefix 4 -gpu -stop

# Signature grinding
VanitySearch.exe -sig -tx CAFEBEEF --prefix 4 \
  -z AAAA...64hex -d BBBB...64hex -gpu -stop

# TXID grinding
VanitySearch.exe -txid -raw <tx_hex> -tx DEAD00 --prefix 3 -gpu -stop
```

### Production (40-bit, allow 3 min)

```bash
VanitySearch.exe -mask -tx <10_hex_chars> --prefix 5 -gpu -stop
```

---

## Notes

### Poisson Distribution

Grinding times follow a Poisson distribution:
- 50% complete by expected time
- 90% complete by 2.3x expected
- 99% complete by 4.6x expected

### Thermal Throttling

RTX 4090 may throttle under sustained load, reducing rate by 10-20%. Ensure adequate cooling.

### Startup Overhead

First ~2.5s of each grind is GPU initialization. This is fixed cost regardless of bit depth.

---

**Last Updated:** 2024-12-30
**Tested With:** VanityMask v1.19, Bitcoin Core v28.1.0 (regtest)
