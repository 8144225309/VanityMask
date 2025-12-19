# VanitySearch with Steganography Mode

A fork of VanitySearch with added **steganography mode** - find Bitcoin private keys where the public key X coordinate matches arbitrary bit patterns.

## What's New: Steganography Mode

Traditional vanity search finds addresses starting with specific Base58 characters (like `1Love...`). 

**Steganography mode** operates on the raw public key, letting you:
- Match prefixes of the X coordinate (`DEADBEEF...`)
- Match scattered bytes anywhere (`AA__BB__CC__DD__`)
- Match arbitrary bit patterns with custom masks
- Embed hidden messages in public keys

### Performance

| GPU | Speed |
|-----|-------|
| RTX 4090 | ~27 GKeys/s |
| RTX 3080 | ~15 GKeys/s |
| RTX 2070 | ~8 GKeys/s |

Stego mode is **3-4x faster** than normal vanity search because it skips SHA256 and RIPEMD160 hashing.

---

## Building

### Requirements

**Both Platforms:**
- NVIDIA GPU with Compute Capability 7.5+ (RTX 20xx or newer)
- CUDA Toolkit 11.0+ (tested with CUDA 12/13)

**Windows:**
- Visual Studio 2019 or 2022 with "Desktop development with C++" workload
- CUDA Toolkit with Visual Studio integration

**Linux:**
- GCC 9+ (g++)
- Make
- CUDA Toolkit with nvcc

---

## Windows Build

### Step 1: Install Prerequisites

1. **Visual Studio 2022** (Community edition is free)
   - Download from: https://visualstudio.microsoft.com/
   - During install, select "Desktop development with C++"

2. **CUDA Toolkit**
   - Download from: https://developer.nvidia.com/cuda-downloads
   - Select Windows → x86_64 → your Windows version → exe (local)
   - Install with Visual Studio integration enabled

### Step 2: Build

1. Extract `VanitySearch-Stego.zip`
2. Open `VanitySearch.sln` in Visual Studio
3. Select **Release** and **x64** in the toolbar dropdowns
4. Build → Build Solution (or press **F7**)
5. Wait for build to complete (may take 1-2 minutes for CUDA compilation)

### Step 3: Run

```cmd
cd x64\Release
VanitySearch.exe -gpu -stego -tx DEADBEEF --prefix 4
```

### Troubleshooting Windows Build

**"CUDA not found" errors:**
- Ensure CUDA Toolkit is installed with VS integration
- Restart Visual Studio after CUDA install

**"Platform toolset not found":**
- Right-click project → Properties → General → Platform Toolset
- Select your installed version (v143 for VS 2022, v142 for VS 2019)

**Linker errors about CUDA:**
- Check Project Properties → CUDA C/C++ → Device → Code Generation
- Should include your GPU architecture (e.g., compute_89,sm_89 for RTX 4090)

---

## Linux Build (including WSL2)

### Step 1: Install Prerequisites

**Ubuntu/Debian:**
```bash
# Build essentials
sudo apt update
sudo apt install -y build-essential git

# CUDA Toolkit (if not already installed)
# Option A: From NVIDIA (recommended for latest)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-4

# Option B: From Ubuntu repos (may be older)
sudo apt install -y nvidia-cuda-toolkit
```

**WSL2 Specific:**
```bash
# WSL2 uses Windows GPU driver - just need CUDA toolkit
# Make sure you have latest NVIDIA Windows driver installed first!

# Then in WSL2:
sudo apt update
sudo apt install -y build-essential
sudo apt install -y nvidia-cuda-toolkit
# OR install from NVIDIA repos as shown above
```

### Step 2: Build

```bash
# Extract and enter directory
unzip VanitySearch-Stego.zip
cd VanitySearch-Stego

# Check your GPU's compute capability
nvidia-smi --query-gpu=compute_cap --format=csv
# RTX 4090 = 8.9, RTX 3080 = 8.6, RTX 2070 = 7.5

# Build for your specific GPU (fastest compile, optimized binary)
make gpu=1 CCAP=89 -j$(nproc)    # RTX 4090
# OR
make gpu=1 CCAP=86 -j$(nproc)    # RTX 3080/3090
# OR
make gpu=1 CCAP=75 -j$(nproc)    # RTX 2070/2080

# OR build for multiple architectures (slower compile, runs on any RTX)
make gpu=1 -j$(nproc)
```

### Step 3: Run

```bash
./VanitySearch -gpu -stego -tx DEADBEEF --prefix 4
```

### Troubleshooting Linux Build

**"nvcc: command not found":**
```bash
# Add CUDA to PATH
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Add to ~/.bashrc to make permanent
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
```

**"cuda_runtime.h: No such file":**
```bash
# Specify CUDA path explicitly
make gpu=1 CUDA=/usr/local/cuda-12.4 CCAP=89 -j$(nproc)
```

**"unsupported GNU version" with nvcc:**
```bash
# Use specific GCC version
sudo apt install g++-11
make gpu=1 CXXCUDA=/usr/bin/g++-11 CCAP=89 -j$(nproc)
```

**WSL2: "CUDA driver version insufficient":**
- Update your Windows NVIDIA driver to latest version
- Restart WSL2: `wsl --shutdown` then reopen terminal

**Show build configuration:**
```bash
make info gpu=1 CCAP=89
```

---

## Usage

### Steganography Mode

#### Basic: Match X Coordinate Prefix

```bash
# Match first 4 bytes (32 bits) - ~0.15 seconds
./VanitySearch -gpu -stego -tx DEADBEEF --prefix 4

# Match first 5 bytes (40 bits) - ~40 seconds
./VanitySearch -gpu -stego -tx DEADBEEFAA --prefix 5

# Match first 6 bytes (48 bits) - ~3 hours
./VanitySearch -gpu -stego -tx DEADBEEFAABB --prefix 6
```

#### Advanced: Scattered Byte Patterns

```bash
# Match AA at byte 0, BB at byte 2, CC at byte 4, DD at byte 6
./VanitySearch -gpu -stego \
  -tx AA00BB00CC00DD00000000000000000000000000000000000000000000000000 \
  -mx FF00FF00FF00FF00000000000000000000000000000000000000000000000000

# "CAFE" at start, "BABE" in middle
./VanitySearch -gpu -stego \
  -tx CAFE000000000000000000000000BABE0000000000000000000000000000000000 \
  -mx FFFF000000000000000000000000FFFF0000000000000000000000000000000000
```

### Output Format

```
PubAddress: STEGO:DEADBEEF9CEDE7A287A2D6E4C6D398D8F2C5444B536E2CFCEF75275130E018E2
Priv (WIF): p2pkh:KxKijNaJ3WRLgTan7ivnxiKV9xQa2jYb83QQv87ZTEQ7EQAFf34S  
Priv (HEX): 0x20EDCAAC0157FE219C1B7F6BB0435A86955B4087569D56D4E6DF3F1F38DEB080
```

### Traditional Vanity Mode (Original)

```bash
# Find address starting with "1Love"
./VanitySearch -gpu 1Love

# Case-insensitive
./VanitySearch -gpu -i 1love

# Bech32 (native SegWit)
./VanitySearch -gpu -bech32 bc1qtest
```

---

## CLI Reference

### Stego Flags

| Flag | Description | Example |
|------|-------------|---------|
| `-stego` | Enable steganography mode | `-stego` |
| `-tx <hex>` | Target X coordinate (1-64 hex chars) | `-tx DEADBEEF` |
| `-mx <hex>` | Custom mask (1-64 hex chars) | `-mx FF00FF00` |
| `--prefix <n>` | Match first N bytes (1-32) | `--prefix 4` |

### General Flags

| Flag | Description | Example |
|------|-------------|---------|
| `-gpu` | Use GPU acceleration | `-gpu` |
| `-gpuId <n>` | Select specific GPU | `-gpuId 0` |
| `-stop` | Stop after first match | `-stop` |
| `-o <file>` | Output to file | `-o results.txt` |
| `-t <n>` | Number of CPU threads | `-t 4` |

---

## Difficulty Reference

| Bits | Hex Chars | Time @ 27 GKeys/s |
|------|-----------|-------------------|
| 32 | 8 | 0.16 sec |
| 40 | 10 | 41 sec |
| 48 | 12 | 2.9 hours |
| 56 | 14 | 31 days |
| 64 | 16 | 21 years |

---

## Verifying Results

```python
# pip install ecdsa
from ecdsa import SECP256k1, SigningKey

def verify_stego(priv_hex, expected_prefix):
    priv_hex = priv_hex.replace('0x', '').zfill(64)
    sk = SigningKey.from_string(bytes.fromhex(priv_hex), curve=SECP256k1)
    pk = sk.verifying_key.to_string()
    x_coord = pk[:32].hex().upper()
    print(f"X Coordinate: {x_coord}")
    print(f"Starts with {expected_prefix}: {x_coord.startswith(expected_prefix.upper())}")

verify_stego("20EDCAAC0157FE219C1B7F6BB0435A86955B4087569D56D4E6DF3F1F38DEB080", "DEADBEEF")
```

---

## Files Modified from Original VanitySearch

| File | Changes |
|------|---------|
| `main.cpp` | Added `-stego`, `-tx`, `-mx`, `--prefix` CLI |
| `Vanity.cpp` | Stego key reconstruction with endomorphism fix |
| `Vanity.h` | Added `stegoMode`, `StegoTarget` members |
| `GPU/GPUEngine.cu` | Stego kernel, constant memory, SM 8.9 support |
| `GPU/GPUCompute.h` | `CheckStegoPoint()`, `CheckStegoComp()` functions |
| `StegoTarget.h` | **NEW** - Target/mask parsing utilities |
| `Makefile` | Updated for modern CUDA, multi-arch support |

---

## Technical Documentation

See `STEGO_TECHNICAL_DOCS.md` for:
- Complete architecture documentation
- CUDA implementation details  
- Key reconstruction math
- How to extend to Y coordinate / Hash160 matching

---

## License

VanitySearch is licensed under GPLv3.

## Credits

- Original VanitySearch by [Jean-Luc Pons](https://github.com/JeanLucPons/VanitySearch)
- Steganography mode extension - 2024
