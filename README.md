# VanityMask

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![CUDA](https://img.shields.io/badge/CUDA-12.0%2B-green.svg)](https://developer.nvidia.com/cuda-toolkit)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()
[![Version](https://img.shields.io/badge/Version-1.20-orange.svg)](https://github.com/8144225309/VanityMask/releases)

GPU-accelerated tool for grinding Bitcoin **pubkey coordinates**, **signature R-values**, **transaction IDs**, and **vanity addresses**. Fork of [JeanLucPons/VanitySearch](https://github.com/JeanLucPons/VanitySearch).

Embed arbitrary bit patterns anywhere in your keys or TXIDs.

## Features

### Grinding Modes

| Mode | Flag | What it grinds | Use case |
|------|------|----------------|----------|
| **Pubkey Mask** | `-mask` | Public key X coordinate | Embed data in pubkeys |
| **Signature** | `-sig` | ECDSA/Schnorr R.x value | Embed data in signatures |
| **TXID** | `-txid` | Transaction ID (double SHA256) | Custom TXID prefixes |
| **Vanity** | (default) | Bitcoin address prefix | Custom addresses |

### All Modes Support
- Arbitrary bit positioning with `-mx` mask flag
- Prefix matching with `--prefix N` for first N bytes
- GPU-accelerated (~27 GKey/s EC ops, ~8 MKey/s TXID on RTX 4090)
- Multi-GPU support

### Original VanitySearch Features
- Generate vanity Bitcoin addresses (P2PKH, P2SH, BECH32)
- Multi-GPU support with CUDA optimization
- Split-key vanity generation for third-party searches
- Wildcard pattern matching (`?` and `*`)
- Case-insensitive search option

## Performance

Mask mode benchmarks (RTX 4090):

| Bits | Difficulty | Expected Time |
|------|------------|---------------|
| 32   | 2^32       | ~0.16 sec     |
| 40   | 2^40       | ~41 sec       |
| 48   | 2^48       | ~2.9 hours    |
| 56   | 2^56       | ~31 days      |

## Usage

### Pubkey Mask Mode

Grind a private key whose public key X coordinate matches your target pattern.

```bash
# Match first 4 bytes (32 bits) of X coordinate
./VanitySearch -gpu -mask -tx DEADBEEF --prefix 4 -stop

# Match with explicit mask (any position)
./VanitySearch -gpu -mask \
  -tx 0000000000000000000000000000000000000000000000DEADBEEF00000000 \
  -mx 0000000000000000000000000000000000000000000000FFFFFFFF00000000

# Match first 5 bytes
./VanitySearch -gpu -mask -tx DEADBEEFAA --prefix 5
```

### Signature R-Value Grinding Mode

Grind a nonce k where R.x = k*G matches your target pattern.

```bash
# ECDSA signature with 32-bit R.x prefix
./VanitySearch -gpu -sig -tx DEADBEEF --prefix 4 \
  -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 \
  -d 0000000000000000000000000000000000000000000000000000000000000001

# BIP340 Schnorr signature
./VanitySearch -gpu -sig -tx DEADBEEF --prefix 4 \
  -z <32-byte-msg-hash-hex> \
  -d <32-byte-privkey-hex> \
  --schnorr

# Arbitrary mask position (match middle bytes of R.x)
./VanitySearch -gpu -sig \
  -tx 0000000000000000000000000000000000000000000000DEADBEEF00000000 \
  -mx 0000000000000000000000000000000000000000000000FFFFFFFF00000000 \
  -z <msg-hash> -d <privkey>
```

### TXID Grinding Mode

Grind a transaction's nonce bytes to produce a TXID matching your target prefix.

```bash
# Grind nLockTime (last 4 bytes) for TXID prefix "0000"
./VanitySearch -gpu -txid -raw 0100000001...00000000 -tx 0000 --prefix 2 -stop

# Grind for specific prefix "dead"
./VanitySearch -gpu -txid -raw <full_tx_hex> -tx dead --prefix 2 -stop

# Custom nonce position (offset 50, 4 bytes)
./VanitySearch -gpu -txid -raw <tx_hex> -tx beef --prefix 2 \
  -nonce-offset 50 -nonce-len 4 -stop
```

### Standard Vanity Address Search

```bash
# Find address starting with "1Drew"
./VanitySearch -gpu -stop 1Drew

# Case-insensitive search
./VanitySearch -gpu -c -stop 1drew

# BECH32 address
./VanitySearch -gpu -stop bc1qmy

# Multiple prefixes from file
./VanitySearch -gpu -stop -i prefixes.txt
```

### Command Line Options

```
VanitySearch [-check] [-v] [-u] [-b] [-c] [-gpu] [-stop] [-i inputfile]
             [-gpuId gpuId1[,gpuId2,...]] [-g g1x,g1y,[,g2x,g2y,...]]
             [-o outputfile] [-m maxFound] [-ps seed] [-s seed] [-t nbThread]
             [-nosse] [-r rekey] [-check] [-kp] [-sp startPubKey]
             [-rp privkey partialkeyfile] [prefix]
             [-mask -tx <target_hex> [-mx <mask_hex>] [--prefix <n>]]
             [-sig -tx <target_hex> -z <msghash> -d <privkey> [--schnorr]]

Standard options:
  prefix          : Prefix to search (can contain wildcards '?' or '*')
  -v              : Print version
  -u              : Search uncompressed addresses
  -b              : Search both uncompressed and compressed addresses
  -c              : Case-insensitive search
  -gpu            : Enable GPU calculation
  -stop           : Stop when all prefixes are found
  -i inputfile    : Get prefixes from file
  -o outputfile   : Output results to file
  -gpuId 0,1,...  : List of GPUs to use (default: 0)
  -g x,y,...      : GPU grid size (default: 8*MP,128)
  -m maxFound     : Max prefixes per kernel call
  -s seed         : Seed for base key (default: random)
  -ps seed        : Seed with added crypto-secure random
  -t threads      : Number of CPU threads
  -nosse          : Disable SSE hash functions
  -l              : List CUDA devices
  -check          : Verify CPU/GPU kernel correctness
  -kp             : Generate key pair
  -sp pubkey      : Start with public key (split-key mode)
  -rp priv file   : Reconstruct private key from partial
  -r rekey        : Rekey interval in MegaKeys

Pubkey mask options:
  -mask           : Enable pubkey coordinate masking
  -tx <hex>       : Target X coordinate (1-64 hex chars)
  -mx <hex>       : Mask for X coordinate (optional)
  --prefix <n>    : Match first N bytes (1-32)

Signature grinding options:
  -sig            : Enable signature grinding mode
  -tx <hex>       : Target R.x value (1-64 hex chars)
  -mx <hex>       : Mask for R.x (optional)
  -z <hex>        : Message hash to sign (32-byte hex)
  -d <hex>        : Signing private key (32-byte hex)
  --schnorr       : Use BIP340 Schnorr instead of ECDSA
  --prefix <n>    : Match first N bytes of R.x (1-32)

TXID grinding options:
  -txid           : Enable TXID grinding mode
  -raw <hex>      : Raw transaction hex
  -tx <hex>       : Target TXID pattern (1-64 hex chars)
  -mx <hex>       : Mask for TXID (optional)
  --prefix <n>    : Match first N bytes of TXID (1-32)
  -nonce-offset N : Byte offset of nonce in tx (default: last 4 bytes)
  -nonce-len N    : Number of nonce bytes (1-8, default: 4)
```

## Building

### Windows (Visual Studio 2017+)

1. Install [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
2. Open `VanitySearch.sln`
3. Set Windows SDK version in project properties if needed
4. Build in Release configuration

Note: Update CUDA paths in `.vcxproj` if using a different CUDA version.

### Linux

```bash
# Install CUDA SDK first

# CPU-only build
make all

# GPU build (adjust CCAP for your GPU)
make gpu=1 CCAP=8.9 all
```

Edit `Makefile` to set CUDA paths:
```makefile
CUDA       = /usr/local/cuda-12.0
CXXCUDA    = /usr/bin/g++
```

Common compute capabilities:
- RTX 4090/4080: 8.9
- RTX 3090/3080: 8.6
- RTX 2080: 7.5
- GTX 1080: 6.1

### Docker

```bash
# CPU build
./docker/cpu/build.sh

# GPU build
env CCAP=8.9 CUDA=12.0 ./docker/cuda/build.sh

# Run
docker run -it --rm --gpus all --network none vanitysearch -gpu -stop 1Test
```

## Examples

### Vanity Address Generation

```
$ ./VanitySearch -gpu -stop 1Drew
VanitySearch v1.20
Difficulty: 264104224
Search: 1Drew [Compressed]
Start Fri Dec 19 12:00:00 2025
Base Key: A1B2C3D4E5F6...
Number of CPU thread: 7
GPU: GPU #0 NVIDIA GeForce RTX 4090 (128x128 cores) Grid(1024x128)
[27542.81 Mkey/s][GPU 26144.42 Mkey/s][Total 2^33.12][Prob 78.2%][Found 1]

PubAddress: 1DrewXyz123abc456def789ghi012jkl
Priv (WIF): p2pkh:KxYz...
Priv (HEX): 0x123ABC...
```

### Pubkey Mask Mode

```
$ ./VanitySearch -gpu -mask -tx DEADBEEF --prefix 4
VanitySearch v1.20
=== PUBKEY MASK MODE ===
Target X:   deadbeef00000000000000000000000000000000000000000000000000000000
Mask:       ffffffff00000000000000000000000000000000000000000000000000000000
Bits:       32 (difficulty 2^32)
Estimate:   0.16 sec @ 27 GKeys/s
========================
GPU: GPU #0 NVIDIA GeForce RTX 4090 (128x128 cores) Grid(1024x128)
[27688.04 Mkey/s][GPU 26144.42 Mkey/s][Total 2^32.04][Prob 51.2%][Found 1]

PubAddress: MASK:DEADBEEF1A2B3C4D5E6F...
Priv (WIF): p2pkh:Kx...
Priv (HEX): 0x...
```

### Signature R-Value Grinding

```
$ ./VanitySearch -gpu -sig -tx DEADBEEF --prefix 4 \
    -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 \
    -d 0000000000000000000000000000000000000000000000000000000000000001
VanitySearch v1.20
=== SIGNATURE R-VALUE GRINDING MODE ===
Target R.x: deadbeef00000000000000000000000000000000000000000000000000000000
Mask:       ffffffff00000000000000000000000000000000000000000000000000000000
Bits:       32 (difficulty 2^32)
Mode:       ECDSA
Msg Hash:   0102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F20
Sign Key:   1...
Estimate:   0.16 sec @ 27 GKeys/s
=======================================
GPU: GPU #0 NVIDIA GeForce RTX 4090 (128x128 cores) Grid(1024x128)

=== SIGNATURE FOUND ===
Nonce (k):  ABC123...
R.x:        DEADBEEF1A2B3C4D...
R.y parity: even
sig.r:      DEADBEEF1A2B3C4D...
sig.s:      7F8E9D0C1B2A3948...
Mode:       ECDSA
========================
```

## Split-Key Generation

Generate vanity addresses for third parties without exposing private keys:

**Step 1: Requester generates keypair**
```bash
./VanitySearch -kp
Priv : L4U2Ca2wyo721n7j9nXM9oUWLzCj19nKtLeJuTXZP3AohW9wVgrH
Pub  : 03FC71AE1E88F143E8B05326FC9A83F4DAB93EA88FFEACD37465ED843FCC75AA81
```

**Step 2: Searcher finds match using public key**
```bash
./VanitySearch -sp 03FC71AE1E88F143E8B05326FC9A83F4DAB93EA88FFEACD37465ED843FCC75AA81 -gpu -stop -o keyinfo.txt 1Alice
```

**Step 3: Requester reconstructs final key**
```bash
./VanitySearch -rp L4U2Ca2wyo721n7j9nXM9oUWLzCj19nKtLeJuTXZP3AohW9wVgrH keyinfo.txt
```

## Technical Details

### How Mask Mode Works

In standard mode, VanitySearch:
1. Generates keypairs (private key → public key)
2. Hashes public key (SHA256 → RIPEMD160)
3. Encodes as Base58/Bech32 address
4. Compares against target prefix

In mask mode:
1. Generates keypairs (private key → public key)
2. Compares raw X coordinate against target using bitmask
3. Skips hashing entirely → 3-4x faster

Both `-mask` and `-sig` modes use the same GPU kernel - they're just grinding different EC points (pubkey vs signature R).

### Endomorphism Optimization

VanitySearch uses secp256k1's efficiently-computable endomorphism to get 6 keys per scalar multiplication:
- Original point P
- Endomorphism #1: (βx, y)
- Endomorphism #2: (β²x, y)
- Negations of all three: (x, -y)

This 6x multiplier applies to all modes.

## License

GPLv3 - See [LICENSE.txt](LICENSE.txt)

## Credits

- Original VanitySearch by [Jean Luc Pons](https://github.com/JeanLucPons)
- Mask/signature modes by [8144225309](https://github.com/8144225309)
