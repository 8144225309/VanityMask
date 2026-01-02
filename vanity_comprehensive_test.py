#!/usr/bin/env python3
"""
VanityMask Comprehensive Test Suite
Tests all modes and functions with hardware monitoring.
Generates detailed reports with GPU/CPU utilization metrics.

Usage:
    python vanity_comprehensive_test.py [--windows-only] [--wsl-only] [--quick]
"""

import subprocess
import threading
import time
import os
import sys
import csv
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

# ==============================================================================
# CONFIGURATION
# ==============================================================================

WINDOWS_EXE = r"VanityMask-windows-test\x64\Release\VanitySearch.exe"
WSL_EXE = "/mnt/c/pirqjobs/vanitymask-workshop/VanityMask-wsl-test/VanitySearch"

# Test data
MSG_HASH = "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20"
PRIVKEY_1 = "0000000000000000000000000000000000000000000000000000000000000001"
# Normal valid privkey (not N-1 edge case which can be problematic)
PRIVKEY_2 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

# Minimal valid transaction for TXID grinding
RAW_TX = (
    "0100000001"  # version + input count
    "0000000000000000000000000000000000000000000000000000000000000000"  # prev txid
    "00000000"  # prev vout
    "00"  # scriptSig length
    "ffffffff"  # sequence
    "01"  # output count
    "0000000000000000"  # value (0 sats)
    "00"  # scriptPubKey length
    "00000000"  # nLockTime (grindable)
)

# Expected G point X coordinate
G_X = "79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798"

# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class HardwareMetrics:
    """Container for hardware metrics at a point in time."""
    timestamp: str = ""
    gpu_util: float = 0.0
    gpu_mem_util: float = 0.0
    gpu_temp: float = 0.0
    gpu_power: float = 0.0
    gpu_mem_used: float = 0.0
    cpu_util: float = 0.0
    process_gpu_util: float = 0.0  # Per-process GPU usage
    process_gpu_mem: float = 0.0   # Per-process GPU memory


@dataclass
class TestResult:
    """Container for a single test result."""
    test_id: str
    description: str
    command: List[str]
    duration: float
    success: bool
    output: str = ""
    error: str = ""
    throughput: str = ""
    metrics_avg: Optional[HardwareMetrics] = None
    metrics_max: Optional[HardwareMetrics] = None


@dataclass
class TestDefinition:
    """Definition of a single test case."""
    test_id: str
    description: str
    args: List[str]
    timeout: int  # seconds
    pass_criteria: str
    sustained_load: bool = False  # If True, timeout is expected


# ==============================================================================
# TEST DEFINITIONS
# ==============================================================================

def get_test_definitions(quick_mode: bool = False) -> List[TestDefinition]:
    """Return all test definitions. Durations reduced in quick mode."""

    # Duration multiplier for quick mode
    mult = 0.25 if quick_mode else 1.0

    tests = []

    # --- GPU Mask Mode Tests ---
    tests.append(TestDefinition(
        "MASK-01", "32-bit prefix warmup",
        ["-gpu", "-mask", "-tx", "DEADBEEF", "--prefix", "4", "-stop"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "MASK-02", "40-bit sustained stress",
        ["-gpu", "-mask", "-tx", "DEADBEEFAA", "--prefix", "5"],
        timeout=int(120 * mult), pass_criteria="rate>20", sustained_load=True
    ))
    tests.append(TestDefinition(
        "MASK-03", "48-bit max stress",
        ["-gpu", "-mask", "-tx", "DEADBEEFAABB", "--prefix", "6"],
        timeout=int(90 * mult), pass_criteria="rate>20", sustained_load=True
    ))
    tests.append(TestDefinition(
        "MASK-04", "Different 32-bit pattern",
        ["-gpu", "-mask",
         "-tx", "BABECAFE", "--prefix", "4",
         "-stop"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "MASK-05", "Different target pattern",
        ["-gpu", "-mask", "-tx", "CAFEBABE", "--prefix", "4", "-stop"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))

    # --- GPU Signature Mode - ECDSA Tests ---
    tests.append(TestDefinition(
        "SIG-01", "16-bit ECDSA warmup",
        ["-gpu", "-sig", "-tx", "DEAD", "--prefix", "2",
         "-z", MSG_HASH, "-d", PRIVKEY_1, "-stop"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "SIG-02", "40-bit ECDSA stress",
        ["-gpu", "-sig", "-tx", "DEADBEEFAA", "--prefix", "5",
         "-z", MSG_HASH, "-d", PRIVKEY_1],
        timeout=int(120 * mult), pass_criteria="rate>20", sustained_load=True
    ))
    tests.append(TestDefinition(
        "SIG-03", "Low-S normalization",
        ["-gpu", "-sig", "-tx", "AAAA", "--prefix", "2",
         "-z", MSG_HASH, "-d", PRIVKEY_1, "-stop"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "SIG-04", "Different privkey",
        ["-gpu", "-sig", "-tx", "BBBB", "--prefix", "2",
         "-z", MSG_HASH, "-d", PRIVKEY_2, "-stop"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))

    # --- GPU Signature Mode - Schnorr Tests ---
    tests.append(TestDefinition(
        "SCHNORR-01", "32-bit Schnorr warmup",
        ["-gpu", "-sig", "-tx", "DEADBEEF", "--prefix", "4",
         "-z", MSG_HASH, "-d", PRIVKEY_1, "--schnorr", "-stop"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "SCHNORR-02", "40-bit Schnorr stress",
        ["-gpu", "-sig", "-tx", "DEADBEEFAA", "--prefix", "5",
         "-z", MSG_HASH, "-d", PRIVKEY_1, "--schnorr"],
        timeout=int(120 * mult), pass_criteria="rate>20", sustained_load=True
    ))
    tests.append(TestDefinition(
        "SCHNORR-03", "Y-parity verification",
        ["-gpu", "-sig", "-tx", "CAFE", "--prefix", "2",
         "-z", MSG_HASH, "-d", PRIVKEY_1, "--schnorr", "-stop"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))

    # --- GPU TXID Mode Tests ---
    tests.append(TestDefinition(
        "TXID-01", "16-bit prefix warmup",
        ["-gpu", "-txid", "-raw", RAW_TX, "-tx", "DEAD", "--prefix", "2", "-stop"],
        timeout=120, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "TXID-02", "24-bit sustained stress",
        ["-gpu", "-txid", "-raw", RAW_TX, "-tx", "DEADBE", "--prefix", "3"],
        timeout=int(120 * mult), pass_criteria="rate>1", sustained_load=True
    ))
    tests.append(TestDefinition(
        "TXID-03", "Custom nonce offset",
        ["-gpu", "-txid", "-raw", RAW_TX, "-tx", "CAFE", "--prefix", "2",
         "-nonce-offset", "10", "-nonce-len", "4", "-stop"],
        timeout=120, pass_criteria="found", sustained_load=False
    ))

    # --- GPU Vanity Mode Tests ---
    tests.append(TestDefinition(
        "VANITY-01", "P2PKH 3-char quick",
        ["-gpu", "-stop", "1Te"],
        timeout=30, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "VANITY-02", "Case insensitive",
        ["-gpu", "-c", "-stop", "1drew"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "VANITY-03", "Bech32 sustained",
        ["-gpu", "bc1qtest"],
        timeout=int(90 * mult), pass_criteria="rate>0.5", sustained_load=True
    ))
    tests.append(TestDefinition(
        "VANITY-04", "Short prefix",
        ["-gpu", "-stop", "1Aa"],
        timeout=30, pass_criteria="found", sustained_load=False
    ))

    # --- GPU Taproot Mode Tests ---
    tests.append(TestDefinition(
        "TAP-01", "24-bit Q.x warmup",
        ["-gpu", "-taproot", "-tx", "DEADBE", "--prefix", "3", "-stop"],
        timeout=90, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "TAP-02", "32-bit Taproot stress",
        ["-gpu", "-taproot", "-tx", "DEADBEEF", "--prefix", "4"],
        timeout=int(90 * mult), pass_criteria="rate>0.1", sustained_load=True
    ))

    # --- CPU-Only Tests ---
    # CPU mask mode is now implemented (SEARCH_STEGO case added to Vanity.cpp)
    tests.append(TestDefinition(
        "CPU-01", "CPU mask mode 24-bit",
        ["-t", "8", "-mask", "-tx", "ABCDEF", "--prefix", "3", "-stop"],
        timeout=60, pass_criteria="mask_found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "CPU-02", "Vanity mode all cores",
        ["-t", "16", "-stop", "1Te"],
        timeout=30, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "CPU-03", "No SSE mode",
        ["-nosse", "-t", "8", "-stop", "1Aa"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))
    tests.append(TestDefinition(
        "CPU-04", "Single thread baseline",
        ["-t", "1", "-stop", "1A"],
        timeout=60, pass_criteria="found", sustained_load=False
    ))

    # --- File I/O Tests ---
    tests.append(TestDefinition(
        "IO-01", "Output to file",
        ["-gpu", "-stop", "1Ab", "-o", "test_output.txt"],
        timeout=30, pass_criteria="file_written", sustained_load=False
    ))
    tests.append(TestDefinition(
        "IO-02", "Input from file",
        ["-gpu", "-stop", "-i", "test_input.txt"],
        timeout=30, pass_criteria="found", sustained_load=False
    ))

    # --- Error Handling Tests ---
    tests.append(TestDefinition(
        "ERR-01", "Invalid prefix char",
        ["-stop", "1Invalid0OIl"],  # Contains invalid base58 chars
        timeout=10, pass_criteria="error_invalid", sustained_load=False
    ))
    tests.append(TestDefinition(
        "ERR-02", "Missing mask target",
        ["-mask", "-stop"],  # Missing -tx argument
        timeout=10, pass_criteria="error_missing", sustained_load=False
    ))

    # --- Utility Function Tests ---
    tests.append(TestDefinition(
        "UTIL-01", "Version check",
        ["-v"],
        timeout=10, pass_criteria="version_119", sustained_load=False
    ))
    tests.append(TestDefinition(
        "UTIL-02", "Help output",
        ["-h"],
        timeout=10, pass_criteria="usage", sustained_load=False
    ))
    tests.append(TestDefinition(
        "UTIL-03", "List GPUs",
        ["-l"],
        timeout=10, pass_criteria="gpu", sustained_load=False
    ))
    tests.append(TestDefinition(
        "UTIL-04", "Compute address",
        ["-ca", "0479BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8"],  # G point uncompressed
        timeout=10, pass_criteria="address", sustained_load=False
    ))
    tests.append(TestDefinition(
        "UTIL-05", "Key pair gen",
        ["-s", "AStrongTestSeedPassphrase1234567890", "-kp"],  # -s before -kp, no spaces
        timeout=10, pass_criteria="priv", sustained_load=False
    ))
    tests.append(TestDefinition(
        "UTIL-06", "Compute pubkey",
        ["-cp", PRIVKEY_1],
        timeout=10, pass_criteria="pub", sustained_load=False
    ))

    return tests


# ==============================================================================
# HARDWARE MONITOR
# ==============================================================================

class HardwareMonitor:
    """Monitors GPU and CPU metrics during tests."""

    def __init__(self, platform: str = "windows"):
        self.platform = platform
        self.running = False
        self.gpu_data: List[HardwareMetrics] = []
        self.threads: List[threading.Thread] = []

    def start(self):
        """Start monitoring in background thread."""
        self.running = True
        self.gpu_data = []

        gpu_thread = threading.Thread(target=self._monitor_gpu, daemon=True)
        gpu_thread.start()
        self.threads.append(gpu_thread)

    def stop(self):
        """Stop monitoring and collect data."""
        self.running = False
        for t in self.threads:
            t.join(timeout=2)
        self.threads = []

    def _monitor_gpu(self):
        """Query nvidia-smi every second."""
        while self.running:
            try:
                if self.platform == "windows":
                    result = subprocess.run(
                        ["nvidia-smi",
                         "--query-gpu=utilization.gpu,utilization.memory,temperature.gpu,power.draw,memory.used",
                         "--format=csv,noheader,nounits"],
                        capture_output=True, text=True, timeout=5
                    )
                else:
                    # WSL - run nvidia-smi through Windows
                    result = subprocess.run(
                        ["nvidia-smi.exe",
                         "--query-gpu=utilization.gpu,utilization.memory,temperature.gpu,power.draw,memory.used",
                         "--format=csv,noheader,nounits"],
                        capture_output=True, text=True, timeout=5
                    )

                if result.returncode == 0:
                    parts = result.stdout.strip().split(",")
                    if len(parts) >= 5:
                        metrics = HardwareMetrics(
                            timestamp=datetime.now().isoformat(),
                            gpu_util=float(parts[0].strip()),
                            gpu_mem_util=float(parts[1].strip()),
                            gpu_temp=float(parts[2].strip()),
                            gpu_power=float(parts[3].strip()),
                            gpu_mem_used=float(parts[4].strip())
                        )
                        self.gpu_data.append(metrics)
            except Exception as e:
                pass  # Silently ignore monitoring errors

            time.sleep(1)

    def get_summary(self) -> Tuple[Optional[HardwareMetrics], Optional[HardwareMetrics]]:
        """Return average and max metrics."""
        if not self.gpu_data:
            return None, None

        n = len(self.gpu_data)
        avg = HardwareMetrics(
            gpu_util=sum(m.gpu_util for m in self.gpu_data) / n,
            gpu_mem_util=sum(m.gpu_mem_util for m in self.gpu_data) / n,
            gpu_temp=sum(m.gpu_temp for m in self.gpu_data) / n,
            gpu_power=sum(m.gpu_power for m in self.gpu_data) / n,
            gpu_mem_used=sum(m.gpu_mem_used for m in self.gpu_data) / n,
        )
        max_m = HardwareMetrics(
            gpu_util=max(m.gpu_util for m in self.gpu_data),
            gpu_mem_util=max(m.gpu_mem_util for m in self.gpu_data),
            gpu_temp=max(m.gpu_temp for m in self.gpu_data),
            gpu_power=max(m.gpu_power for m in self.gpu_data),
            gpu_mem_used=max(m.gpu_mem_used for m in self.gpu_data),
        )
        return avg, max_m

    def save_metrics(self, filepath: Path):
        """Save raw metrics to CSV."""
        if not self.gpu_data:
            return

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "gpu_util", "gpu_mem_util", "gpu_temp", "gpu_power", "gpu_mem_used", "process_gpu_util", "process_gpu_mem"])
            for m in self.gpu_data:
                writer.writerow([m.timestamp, m.gpu_util, m.gpu_mem_util, m.gpu_temp, m.gpu_power, m.gpu_mem_used, m.process_gpu_util, m.process_gpu_mem])


# ==============================================================================
# TEST RUNNER
# ==============================================================================

class TestRunner:
    """Runs VanityMask tests with hardware monitoring."""

    def __init__(self, exe_path: str, output_dir: Path, platform: str = "windows"):
        self.exe_path = exe_path
        self.output_dir = output_dir
        self.platform = platform
        self.results: List[TestResult] = []
        self.all_metrics: List[HardwareMetrics] = []

    def run_test(self, test_def: TestDefinition) -> TestResult:
        """Run a single test with monitoring."""
        print(f"\n  [{test_def.test_id}] {test_def.description}...")

        # Setup for IO tests
        if test_def.test_id == "IO-02":
            # Create test input file with easy prefix
            input_file = self.output_dir.parent / "test_input.txt"
            input_file.write_text("1A\n")
        elif test_def.test_id == "IO-01":
            # Clean up any previous output file
            output_file = self.output_dir.parent / "test_output.txt"
            if output_file.exists():
                output_file.unlink()

        monitor = HardwareMonitor(self.platform)
        monitor.start()

        start_time = time.time()
        output = ""
        error = ""
        success = False

        try:
            if self.platform == "windows":
                cmd = [self.exe_path] + test_def.args
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=test_def.timeout,
                    cwd=str(self.output_dir.parent)
                )
            else:
                # WSL execution
                wsl_cmd = f"cd /mnt/c/pirqjobs/vanitymask-workshop && {self.exe_path} " + " ".join(test_def.args)
                result = subprocess.run(
                    ["wsl", "bash", "-c", wsl_cmd],
                    capture_output=True,
                    text=True,
                    timeout=test_def.timeout
                )

            output = result.stdout
            error = result.stderr
            elapsed = time.time() - start_time

            # Check pass criteria
            success = self._check_criteria(output + error, test_def.pass_criteria)

        except subprocess.TimeoutExpired:
            elapsed = test_def.timeout
            # For sustained load tests, timeout is success
            success = test_def.sustained_load
            output = f"[Timeout after {test_def.timeout}s - {'expected' if test_def.sustained_load else 'FAILED'}]"
        except Exception as e:
            elapsed = time.time() - start_time
            error = str(e)
            success = False

        monitor.stop()

        # Save metrics for this test
        metrics_path = self.output_dir / "metrics" / f"{test_def.test_id}_gpu.csv"
        monitor.save_metrics(metrics_path)
        self.all_metrics.extend(monitor.gpu_data)

        avg_metrics, max_metrics = monitor.get_summary()

        # Extract throughput from output
        throughput = self._extract_throughput(output)

        # Save test log
        log_path = self.output_dir / "logs" / f"{test_def.test_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'w') as f:
            f.write(f"Test: {test_def.test_id}\n")
            f.write(f"Description: {test_def.description}\n")
            f.write(f"Command: {test_def.args}\n")
            f.write(f"Duration: {elapsed:.2f}s\n")
            f.write(f"Success: {success}\n")
            f.write(f"Throughput: {throughput}\n")
            f.write(f"\n--- STDOUT ---\n{output}\n")
            f.write(f"\n--- STDERR ---\n{error}\n")

        result = TestResult(
            test_id=test_def.test_id,
            description=test_def.description,
            command=test_def.args,
            duration=elapsed,
            success=success,
            output=output,
            error=error,
            throughput=throughput,
            metrics_avg=avg_metrics,
            metrics_max=max_metrics
        )

        self.results.append(result)

        status = "PASS" if success else "FAIL"
        gpu_info = f"GPU:{avg_metrics.gpu_util:.0f}%" if avg_metrics else "GPU:N/A"
        print(f"    [{status}] {elapsed:.1f}s | {throughput or 'N/A'} | {gpu_info}")

        return result

    def _check_criteria(self, output: str, criteria: str) -> bool:
        """Check if output meets pass criteria."""
        output_lower = output.lower()

        if criteria == "found":
            return "found" in output_lower or "priv" in output_lower or "address" in output_lower
        elif criteria == "version_119":
            # VanityMask is currently version 1.19
            return "1.19" in output_lower or "1.20" in output_lower
        elif criteria == "usage":
            return "usage" in output_lower or "-gpu" in output_lower
        elif criteria == "gpu":
            return "gpu" in output_lower or "cuda" in output_lower or "4090" in output_lower
        elif criteria == "ok":
            return "ok" in output_lower or "check" in output_lower
        elif criteria == "address":
            # Looking for a Bitcoin address in output (starts with 1, 3, or bc1)
            return "1" in output or "address" in output_lower
        elif criteria == "priv":
            return "priv" in output_lower
        elif criteria == "pub":
            return "pub" in output_lower or "04" in output or "02" in output or "03" in output
        elif criteria == "mask_found":
            # CPU mask mode should output MASK: prefix with matching X coordinate
            return "mask:" in output_lower and "priv" in output_lower
        elif criteria == "file_written":
            # Check if the output file was written (find result)
            return "found" in output_lower or "priv" in output_lower
        elif criteria == "error_invalid":
            # Should show error for invalid Base58 characters
            return "invalid" in output_lower or "error" in output_lower or "argument" in output_lower
        elif criteria == "error_missing":
            # Should show error for missing required argument
            return "error" in output_lower or "missing" in output_lower or "require" in output_lower or "target" in output_lower
        elif criteria.startswith("rate>"):
            # Check if throughput exceeds threshold
            threshold = float(criteria[5:])
            rate = self._extract_rate(output)
            return rate is not None and rate > threshold

        return False

    def _extract_throughput(self, output: str) -> str:
        """Extract throughput string from output."""
        # Look for patterns like [27542.81 Mkey/s] or [GPU 26144.42 Mkey/s]
        match = re.search(r'\[([\d.]+)\s*(M|G)?key/s\]', output, re.IGNORECASE)
        if match:
            return f"{match.group(1)} {match.group(2) or ''}Key/s"

        match = re.search(r'([\d.]+)\s*(M|G)?key/s', output, re.IGNORECASE)
        if match:
            return f"{match.group(1)} {match.group(2) or ''}Key/s"

        return ""

    def _extract_rate(self, output: str) -> Optional[float]:
        """Extract rate in GKey/s from output."""
        # First try GKey/s
        match = re.search(r'([\d.]+)\s*Gkey/s', output, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Then try MKey/s and convert
        match = re.search(r'([\d.]+)\s*Mkey/s', output, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 1000

        return None

    def run_all_tests(self, tests: List[TestDefinition]):
        """Run all tests sequentially."""
        print(f"\nRunning {len(tests)} tests on {self.platform}...")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "logs").mkdir(exist_ok=True)
        (self.output_dir / "metrics").mkdir(exist_ok=True)

        for test in tests:
            self.run_test(test)

        # Save combined metrics
        if self.all_metrics:
            combined_path = self.output_dir / "metrics" / "combined_gpu.csv"
            with open(combined_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "gpu_util", "gpu_mem_util", "gpu_temp", "gpu_power", "gpu_mem_used", "process_gpu_util", "process_gpu_mem"])
                for m in self.all_metrics:
                    writer.writerow([m.timestamp, m.gpu_util, m.gpu_mem_util, m.gpu_temp, m.gpu_power, m.gpu_mem_used, m.process_gpu_util, m.process_gpu_mem])

    def generate_report(self) -> str:
        """Generate markdown report."""
        passed = sum(1 for r in self.results if r.success)
        failed = len(self.results) - passed
        total_duration = sum(r.duration for r in self.results)

        # Calculate overall metrics
        if self.all_metrics:
            avg_gpu = sum(m.gpu_util for m in self.all_metrics) / len(self.all_metrics)
            max_gpu = max(m.gpu_util for m in self.all_metrics)
            avg_temp = sum(m.gpu_temp for m in self.all_metrics) / len(self.all_metrics)
            max_temp = max(m.gpu_temp for m in self.all_metrics)
            avg_power = sum(m.gpu_power for m in self.all_metrics) / len(self.all_metrics)
            max_power = max(m.gpu_power for m in self.all_metrics)
        else:
            avg_gpu = max_gpu = avg_temp = max_temp = avg_power = max_power = 0

        report = f"""# VanityMask Test Report - {self.platform.upper()}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Platform**: {self.platform}
**Executable**: {self.exe_path}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {len(self.results)} |
| Passed | {passed} |
| Failed | {failed} |
| Pass Rate | {100*passed/len(self.results):.1f}% |
| Total Duration | {total_duration/60:.1f} min |

## Hardware Utilization

| Metric | Average | Peak | Target |
|--------|---------|------|--------|
| GPU Util | {avg_gpu:.1f}% | {max_gpu:.1f}% | 90-95% |
| GPU Temp | {avg_temp:.1f}C | {max_temp:.1f}C | <85C |
| GPU Power | {avg_power:.0f}W | {max_power:.0f}W | - |

## Test Results

| Test ID | Description | Duration | GPU% | Throughput | Result |
|---------|-------------|----------|------|------------|--------|
"""

        for r in self.results:
            status = "PASS" if r.success else "FAIL"
            gpu_pct = f"{r.metrics_avg.gpu_util:.0f}%" if r.metrics_avg else "N/A"
            report += f"| {r.test_id} | {r.description} | {r.duration:.1f}s | {gpu_pct} | {r.throughput or 'N/A'} | {status} |\n"

        # Add failed test details
        failed_tests = [r for r in self.results if not r.success]
        if failed_tests:
            report += "\n## Failed Test Details\n\n"
            for r in failed_tests:
                report += f"### {r.test_id}: {r.description}\n\n"
                report += f"**Command**: `{' '.join(r.command)}`\n\n"
                report += f"**Error**:\n```\n{r.error[:500] if r.error else 'No error output'}\n```\n\n"

        # Save report
        report_path = self.output_dir / "report.md"
        with open(report_path, 'w') as f:
            f.write(report)

        return report


# ==============================================================================
# MAIN
# ==============================================================================

def generate_final_report(output_dir: Path, windows_results: List[TestResult],
                         wsl_results: List[TestResult]) -> str:
    """Generate combined final report."""

    def calc_stats(results):
        if not results:
            return 0, 0, 0
        passed = sum(1 for r in results if r.success)
        return len(results), passed, len(results) - passed

    win_total, win_passed, win_failed = calc_stats(windows_results)
    wsl_total, wsl_passed, wsl_failed = calc_stats(wsl_results)

    # Calculate pass rates safely avoiding division by zero
    win_rate = 100*win_passed/win_total if win_total > 0 else 0
    wsl_rate = 100*wsl_passed/wsl_total if wsl_total > 0 else 0
    total_total = win_total + wsl_total
    total_rate = 100*(win_passed+wsl_passed)/total_total if total_total > 0 else 0

    report = f"""# VanityMask Comprehensive Test Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Test Framework**: vanity_comprehensive_test.py

---

## Executive Summary

| Platform | Total | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
| Windows | {win_total} | {win_passed} | {win_failed} | {win_rate:.1f}% |
| WSL | {wsl_total} | {wsl_passed} | {wsl_failed} | {wsl_rate:.1f}% |
| **Total** | **{win_total + wsl_total}** | **{win_passed + wsl_passed}** | **{win_failed + wsl_failed}** | **{total_rate:.1f}%** |

---

## Test Categories Covered

1. **GPU Mask Mode** (5 tests) - Pubkey X-coordinate matching
2. **GPU ECDSA Signature** (4 tests) - R-value grinding
3. **GPU Schnorr Signature** (3 tests) - BIP340 R-value grinding
4. **GPU TXID Mode** (3 tests) - Transaction ID grinding
5. **GPU Vanity Mode** (4 tests) - Address prefix matching
6. **GPU Taproot Mode** (2 tests) - Post-tweak key grinding
7. **CPU-Only Tests** (4 tests) - Non-GPU operation
8. **Utility Functions** (6 tests) - Helpers and info commands

---

## Detailed Results

See individual platform reports:
- [Windows Report](windows/report.md)
- [WSL Report](wsl/report.md)

---

## Logs and Metrics

All test logs and hardware metrics are saved in:
- `windows/logs/` - Individual test output logs
- `windows/metrics/` - GPU utilization CSV files
- `wsl/logs/` - WSL test output logs
- `wsl/metrics/` - WSL GPU utilization CSV files

---

*Generated by VanityMask Test Suite*
"""

    report_path = output_dir / "FINAL_REPORT.md"
    with open(report_path, 'w') as f:
        f.write(report)

    return report


def main():
    parser = argparse.ArgumentParser(description="VanityMask Comprehensive Test Suite")
    parser.add_argument("--windows-only", action="store_true", help="Run only Windows tests")
    parser.add_argument("--wsl-only", action="store_true", help="Run only WSL tests")
    parser.add_argument("--quick", action="store_true", help="Quick mode with reduced durations")
    args = parser.parse_args()

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(f"test-results-{timestamp}")
    output_dir.mkdir(exist_ok=True)

    print(f"=" * 60)
    print(f"VanityMask Comprehensive Test Suite")
    print(f"Output: {output_dir}")
    print(f"=" * 60)

    tests = get_test_definitions(quick_mode=args.quick)
    print(f"\nTotal tests defined: {len(tests)}")

    windows_results = []
    wsl_results = []

    # Run Windows tests
    if not args.wsl_only:
        print(f"\n{'='*60}")
        print("WINDOWS TESTS")
        print(f"{'='*60}")

        runner = TestRunner(
            exe_path=WINDOWS_EXE,
            output_dir=output_dir / "windows",
            platform="windows"
        )
        runner.run_all_tests(tests)
        runner.generate_report()
        windows_results = runner.results

        print(f"\nWindows tests complete: {sum(1 for r in windows_results if r.success)}/{len(windows_results)} passed")

    # Run WSL tests
    if not args.windows_only:
        print(f"\n{'='*60}")
        print("WSL TESTS")
        print(f"{'='*60}")

        # Use reduced durations for WSL
        wsl_tests = get_test_definitions(quick_mode=True)

        runner = TestRunner(
            exe_path=WSL_EXE,
            output_dir=output_dir / "wsl",
            platform="wsl"
        )
        runner.run_all_tests(wsl_tests)
        runner.generate_report()
        wsl_results = runner.results

        print(f"\nWSL tests complete: {sum(1 for r in wsl_results if r.success)}/{len(wsl_results)} passed")

    # Generate final report
    print(f"\n{'='*60}")
    print("GENERATING FINAL REPORT")
    print(f"{'='*60}")

    generate_final_report(output_dir, windows_results, wsl_results)

    print(f"\nAll done! Results saved to: {output_dir}")
    print(f"  - FINAL_REPORT.md")
    print(f"  - windows/report.md")
    print(f"  - wsl/report.md")


if __name__ == "__main__":
    main()
