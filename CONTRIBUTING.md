# Contributing to VanityMask

Thank you for your interest in contributing to VanityMask!

## Development Setup

### Windows

1. Install [Visual Studio 2022](https://visualstudio.microsoft.com/) with C++ workload
2. Install [CUDA Toolkit 12.0+](https://developer.nvidia.com/cuda-toolkit)
3. Open `VanitySearch.sln`
4. Build in Release configuration (x64)

### Linux

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install build-essential

# Install CUDA toolkit from NVIDIA

# Build with GPU support (adjust CCAP for your GPU)
make gpu=1 CCAP=89 -j$(nproc)  # RTX 4090
make gpu=1 CCAP=86 -j$(nproc)  # RTX 3080/3090
make gpu=1 CCAP=75 -j$(nproc)  # RTX 2070/2080

# Build CPU-only version
make -j$(nproc)
```

## Compute Capabilities

| GPU Series | CCAP |
|------------|------|
| RTX 4090/4080 | 89 |
| RTX 3090/3080/3070 | 86 |
| RTX 2080/2070 | 75 |
| GTX 1080/1070 | 61 |

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test on both Windows and Linux if possible
5. Ensure GPU kernels work correctly (`-check` flag)
6. Commit with clear, descriptive messages
7. Push to your fork
8. Open a Pull Request with a clear description

## Code Style

- Follow existing code conventions in the project
- Use meaningful variable names
- Comment complex algorithms and GPU kernel optimizations
- Keep GPU kernels optimized for throughput
- Ensure cross-platform compatibility (Windows/Linux)

## Testing

Before submitting a PR, please test:

```bash
# Verify kernel correctness
./VanitySearch -check

# Test mask mode
./VanitySearch -gpu -mask -tx DEADBEEF --prefix 4 -stop

# Test signature mode
./VanitySearch -gpu -sig -tx DEADBEEF --prefix 4 \
  -z 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20 \
  -d 0000000000000000000000000000000000000000000000000000000000000001 -stop
```

## Reporting Bugs

Please use the [bug report template](https://github.com/8144225309/VanityMask/issues/new?template=bug_report.md) in GitHub Issues.

Include:
- Your operating system and version
- GPU model and driver version
- CUDA version
- VanityMask version
- Full command line used
- Complete error output

## Feature Requests

Use the [feature request template](https://github.com/8144225309/VanityMask/issues/new?template=feature_request.md) to suggest new features.

## License

By contributing, you agree that your contributions will be licensed under the [GNU General Public License v3.0](LICENSE.txt).
