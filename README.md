# VanityMask

Fork of [JeanLucPons/VanitySearch](https://github.com/JeanLucPons/VanitySearch) with GPU-accelerated matching of custom bit patterns in public key X/Y/XY coordinates.

VanityMask includes all original VanitySearch functionality for Bitcoin vanity address generation, plus an additional **coordinate targeting mode** for matching arbitrary bit patterns directly in secp256k1 public key coordinates.

## Features

### Original VanitySearch Features
- Generate vanity Bitcoin addresses (P2PKH, P2SH, BECH32)
- Multi-GPU support with CUDA optimization
- CPU parallelization with SSE SHA256/RIPEMD160
- Split-key vanity generation for third-party searches
- Wildcard pattern matching (`?` and `*`)
- Case-insensitive search option

### New: Coordinate Targeting Mode
- Match arbitrary bit patterns in public key X, Y, or full XY coordinates
- GPU-accelerated (~27 GKey/s on RTX 4090)
- 3-4x faster than address mode (skips SHA256/RIPEMD160 hashing)
- Configurable bit masks for partial matching
- Automatic prefix-to-mask conversion

## Performance

Coordinate targeting mode benchmarks (RTX 4090):

| Bits | Difficulty | Expected Time |
|------|------------|---------------|
| 32   | 2^32       | ~0.16 sec     |
| 40   | 2^40       | ~41 sec       |
| 48   | 2^48       | ~2.9 hours    |
| 56   | 2^56       | ~31 days      |

## Usage

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

### Coordinate Targeting Mode

```bash
# Match first 5 bytes (40 bits) of X coordinate
./VanitySearch -gpu -stego -tx DEADBEEFAA --prefix 5

# Match with explicit mask
./VanitySearch -gpu -stego -tx DEADBEEF00000000... -mx FFFFFFFF00000000...

# Full 64-char hex target (matches specified bits only)
./VanitySearch -gpu -stego -tx DEADBEEFAA000000000000000000000000000000000000000000000000000000 --prefix 5
```

### Command Line Options

```
VanitySearch [-check] [-v] [-u] [-b] [-c] [-gpu] [-stop] [-i inputfile]
             [-gpuId gpuId1[,gpuId2,...]] [-g g1x,g1y,[,g2x,g2y,...]]
             [-o outputfile] [-m maxFound] [-ps seed] [-s seed] [-t nbThread]
             [-nosse] [-r rekey] [-check] [-kp] [-sp startPubKey]
             [-rp privkey partialkeyfile] [prefix]
             [-stego -tx <target_hex> [-mx <mask_hex>] [--prefix <n>]]

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

Coordinate targeting options:
  -stego          : Enable coordinate targeting mode
  -tx <hex>       : Target X coordinate (1-64 hex chars)
  -mx <hex>       : Mask for X coordinate (optional)
  --prefix <n>    : Match first N bytes (1-32)
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
VanitySearch v1.19
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

### Coordinate Targeting

```
$ ./VanitySearch -gpu -stego -tx DEADBEEF --prefix 4
VanitySearch v1.19
=== COORDINATE TARGETING MODE ===
Target X: deadbeef00000000000000000000000000000000000000000000000000000000
Mask:     ffffffff00000000000000000000000000000000000000000000000000000000
Bits: 32 (difficulty 2^32)
Estimate: 0.16 sec @ 27 GKeys/s
=============================
Start Fri Dec 19 12:00:00 2025
GPU: GPU #0 NVIDIA GeForce RTX 4090 (128x128 cores) Grid(1024x128)
[27688.04 Mkey/s][GPU 26144.42 Mkey/s][Total 2^32.04][Prob 51.2%][Found 1]

PubKey X: DEADBEEF1A2B3C4D5E6F...
Priv (WIF): p2pkh:Kx...
Priv (HEX): 0x...
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

### How Coordinate Targeting Works

In standard mode, VanitySearch:
1. Generates keypairs (private key → public key)
2. Hashes public key (SHA256 → RIPEMD160)
3. Encodes as Base58/Bech32 address
4. Compares against target prefix

In coordinate targeting mode:
1. Generates keypairs (private key → public key)
2. Compares raw X/Y coordinates against target using bitmask
3. Skips hashing entirely → 3-4x faster

### Endomorphism Optimization

VanitySearch uses secp256k1's efficiently-computable endomorphism to get 6 keys per scalar multiplication:
- Original point P
- Endomorphism #1: (βx, y) 
- Endomorphism #2: (β²x, y)
- Negations of all three: (x, -y)

This 6x multiplier applies to both address and coordinate targeting modes.

## License

GPLv3 - See [LICENSE.txt](LICENSE.txt)

## Credits

- Original VanitySearch by [Jean Luc Pons](https://github.com/JeanLucPons)
- Coordinate targeting mode added by [8144225309](https://github.com/8144225309)
