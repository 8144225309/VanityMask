#!/usr/bin/env python3
"""
VanityMask Benchmark Suite

Performance benchmarks for all GPU modes with regression detection
and resource monitoring (GPU utilization, VRAM, CPU, RAM).

Usage:
    python benchmark_suite.py --quick     # Quick benchmarks (~5 min)
    python benchmark_suite.py --full      # Full benchmarks (~30 min)
    python benchmark_suite.py --mode mask # Single mode test
"""

import subprocess
import sys
import os
import re
import json
import time
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# Import GPU monitoring
try:
    from gpu_monitor import GPUMonitor, get_gpu_memory, check_utilization, UTILIZATION_THRESHOLDS
    GPU_MONITORING_AVAILABLE = True
except ImportError:
    GPU_MONITORING_AVAILABLE = False
    print("WARNING: gpu_monitor.py not found - GPU utilization tracking disabled")

# Try to import psutil for CPU/RAM monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Configuration
SCRIPT_DIR = Path(__file__).parent
VANITYSEARCH_EXE = SCRIPT_DIR.parent / "x64" / "Release" / "VanitySearch.exe"
BASELINES_FILE = SCRIPT_DIR / "benchmark_baselines.json"

# Fixed test values for signature mode
FIXED_Z = "0102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F20"
FIXED_D = "0000000000000000000000000000000000000000000000000000000000000001"

# Minimal transaction for TXID mode (P2PKH, 59 bytes)
MINIMAL_TX = "0100000001000000000000000000000000000000000000000000000000000000000000000000000000ffffffff0100000000000000000000000000"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""
    test_id: str
    mode: str
    bits: int
    iteration: int
    throughput_mkeys: float
    elapsed_sec: float
    found: bool
    private_key: Optional[str] = None
    verified: bool = False
    error: Optional[str] = None
    # GPU resource monitoring
    gpu_util_avg: float = 0.0
    gpu_util_min: float = 0.0
    gpu_util_max: float = 0.0
    gpu_util_samples: int = 0
    vram_used_mb: int = 0
    vram_total_mb: int = 0
    # CPU/RAM monitoring
    cpu_percent: float = 0.0
    ram_used_mb: int = 0


@dataclass
class BenchmarkSummary:
    """Summary of benchmark results for a test."""
    test_id: str
    mode: str
    bits: int
    iterations: int
    avg_throughput_mkeys: float
    min_throughput_mkeys: float
    max_throughput_mkeys: float
    avg_time_sec: float
    success_rate: float
    baseline_throughput: Optional[float] = None
    baseline_diff_pct: Optional[float] = None
    status: str = "PASS"
    # GPU resource monitoring (averages across iterations)
    avg_gpu_util: float = 0.0
    min_gpu_util: float = 0.0
    max_gpu_util: float = 0.0
    avg_vram_mb: int = 0
    gpu_util_target: int = 0
    gpu_util_target_met: bool = False
    # CPU/RAM monitoring
    avg_cpu_percent: float = 0.0
    avg_ram_mb: int = 0


def load_baselines() -> Dict:
    """Load performance baselines from JSON file."""
    if BASELINES_FILE.exists():
        with open(BASELINES_FILE) as f:
            return json.load(f)
    return {}


def save_baselines(baselines: Dict):
    """Save performance baselines to JSON file."""
    with open(BASELINES_FILE, 'w') as f:
        json.dump(baselines, f, indent=2)


def get_gpu_info() -> str:
    """Get GPU name via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip().split('\n')[0]
    except:
        return "Unknown GPU"


def parse_vanitysearch_output(output: str) -> Tuple[float, Optional[str], bool]:
    """
    Parse VanitySearch output to extract throughput and private key.
    Returns: (throughput_mkeys, private_key, found)
    """
    throughput = 0.0
    private_key = None
    found = False

    # Parse throughput: [GPU X.XX Mkey/s] or [GPU X.XX Gkey/s]
    # Look for the last throughput line (from running status)
    for line in output.split('\n'):
        if 'Mkey/s' in line or 'Gkey/s' in line:
            match = re.search(r'\[GPU\s+([\d.]+)\s+(M|G)key/s\]', line)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                throughput = value * 1000 if unit == 'G' else value

    # If no running throughput found, try to parse the estimate from header
    # Format: "Estimate:   X.X seconds @ Y.Y GKeys/s"
    if throughput == 0.0:
        estimate_match = re.search(r'@\s+([\d.]+)\s+(M|G)Keys/s', output, re.IGNORECASE)
        if estimate_match:
            value = float(estimate_match.group(1))
            unit = estimate_match.group(2).upper()
            throughput = value * 1000 if unit == 'G' else value

    # Parse private key
    priv_match = re.search(r'Priv \(HEX\):\s*0x([A-Fa-f0-9]+)', output)
    if priv_match:
        private_key = priv_match.group(1).upper()
        found = True

    return throughput, private_key, found


def run_benchmark(mode: str, bits: int, target: str, extra_args: List[str] = None) -> BenchmarkResult:
    """Run a single benchmark test with resource monitoring."""
    test_id = f"{mode.upper()}-{bits}"

    # Build command
    cmd = [str(VANITYSEARCH_EXE)]

    if mode == "mask":
        cmd.extend(["-mask", "-tx", target, "--prefix", str(bits // 4)])
    elif mode == "sig_ecdsa":
        cmd.extend(["-sig", "-tx", target, "--prefix", str(bits // 4),
                    "-z", FIXED_Z, "-d", FIXED_D])
    elif mode == "sig_schnorr":
        cmd.extend(["-sig", "--schnorr", "-tx", target, "--prefix", str(bits // 4),
                    "-z", FIXED_Z, "-d", FIXED_D])
    elif mode == "taproot":
        cmd.extend(["-taproot", "-tx", target, "--prefix", str(bits // 4)])
    elif mode == "txid":
        cmd.extend(["-txid", "-raw", MINIMAL_TX, "-tx", target, "--prefix", str(bits // 4)])

    cmd.extend(["-gpu", "-stop"])

    if extra_args:
        cmd.extend(extra_args)

    # Initialize resource monitoring
    gpu_monitor = None
    if GPU_MONITORING_AVAILABLE:
        gpu_monitor = GPUMonitor(sample_interval=0.5)
        gpu_monitor.start()

    # Capture initial CPU/RAM
    cpu_start = ram_start = 0
    if PSUTIL_AVAILABLE:
        cpu_start = psutil.cpu_percent(interval=None)
        ram_start = psutil.virtual_memory().used // (1024 * 1024)

    # Run benchmark
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout
        )
        elapsed = time.time() - start_time
        output = result.stdout + result.stderr

        throughput, private_key, found = parse_vanitysearch_output(output)

        # Stop GPU monitoring and collect stats
        gpu_util_avg = gpu_util_min = gpu_util_max = 0.0
        gpu_util_samples = 0
        vram_used = vram_total = 0

        if gpu_monitor:
            gpu_stats = gpu_monitor.stop()
            gpu_util_avg = gpu_stats.avg_util
            gpu_util_min = gpu_stats.min_util
            gpu_util_max = gpu_stats.max_util
            gpu_util_samples = gpu_stats.sample_count

        # Get VRAM usage
        if GPU_MONITORING_AVAILABLE:
            mem_info = get_gpu_memory()
            vram_used = mem_info.get('used_mb', 0)
            vram_total = mem_info.get('total_mb', 0)

        # Get CPU/RAM usage
        cpu_percent = ram_used = 0
        if PSUTIL_AVAILABLE:
            cpu_percent = psutil.cpu_percent(interval=None)
            ram_used = psutil.virtual_memory().used // (1024 * 1024)

        return BenchmarkResult(
            test_id=test_id,
            mode=mode,
            bits=bits,
            iteration=0,
            throughput_mkeys=throughput,
            elapsed_sec=elapsed,
            found=found,
            private_key=private_key,
            gpu_util_avg=gpu_util_avg,
            gpu_util_min=gpu_util_min,
            gpu_util_max=gpu_util_max,
            gpu_util_samples=gpu_util_samples,
            vram_used_mb=vram_used,
            vram_total_mb=vram_total,
            cpu_percent=cpu_percent,
            ram_used_mb=ram_used
        )
    except subprocess.TimeoutExpired:
        # Stop GPU monitoring on timeout
        if gpu_monitor:
            gpu_monitor.stop()
        return BenchmarkResult(
            test_id=test_id,
            mode=mode,
            bits=bits,
            iteration=0,
            throughput_mkeys=0,
            elapsed_sec=300,
            found=False,
            error="Timeout"
        )
    except Exception as e:
        # Stop GPU monitoring on error
        if gpu_monitor:
            gpu_monitor.stop()
        return BenchmarkResult(
            test_id=test_id,
            mode=mode,
            bits=bits,
            iteration=0,
            throughput_mkeys=0,
            elapsed_sec=0,
            found=False,
            error=str(e)
        )


def run_benchmark_iterations(mode: str, bits: int, target: str, iterations: int) -> BenchmarkSummary:
    """Run multiple iterations of a benchmark and compute summary."""
    results = []

    print(f"\n{'='*60}")
    print(f"Benchmark: {mode.upper()}-{bits} ({iterations} iterations)")
    print(f"{'='*60}")

    for i in range(iterations):
        print(f"  Iteration {i+1}/{iterations}...", end=" ", flush=True)
        result = run_benchmark(mode, bits, target)
        result.iteration = i + 1
        results.append(result)

        if result.error:
            print(f"ERROR: {result.error}")
        elif result.found:
            gpu_info = f", GPU:{result.gpu_util_avg:.0f}%" if result.gpu_util_avg > 0 else ""
            print(f"OK - {result.throughput_mkeys:.1f} Mkey/s, {result.elapsed_sec:.3f}s{gpu_info}")
        else:
            print(f"NO MATCH - {result.throughput_mkeys:.1f} Mkey/s")

    # Compute summary
    successful = [r for r in results if r.found and r.throughput_mkeys > 0]

    if successful:
        avg_throughput = sum(r.throughput_mkeys for r in successful) / len(successful)
        min_throughput = min(r.throughput_mkeys for r in successful)
        max_throughput = max(r.throughput_mkeys for r in successful)
        avg_time = sum(r.elapsed_sec for r in successful) / len(successful)
    else:
        avg_throughput = min_throughput = max_throughput = avg_time = 0

    # Compute GPU stats from all results (even unsuccessful ones may have GPU data)
    results_with_gpu = [r for r in results if r.gpu_util_samples > 0]
    if results_with_gpu:
        avg_gpu_util = sum(r.gpu_util_avg for r in results_with_gpu) / len(results_with_gpu)
        min_gpu_util = min(r.gpu_util_min for r in results_with_gpu)
        max_gpu_util = max(r.gpu_util_max for r in results_with_gpu)
        avg_vram = sum(r.vram_used_mb for r in results_with_gpu) // len(results_with_gpu)
    else:
        avg_gpu_util = min_gpu_util = max_gpu_util = 0.0
        avg_vram = 0

    # Compute CPU/RAM stats
    results_with_sys = [r for r in results if r.cpu_percent > 0 or r.ram_used_mb > 0]
    if results_with_sys:
        avg_cpu = sum(r.cpu_percent for r in results_with_sys) / len(results_with_sys)
        avg_ram = sum(r.ram_used_mb for r in results_with_sys) // len(results_with_sys)
    else:
        avg_cpu = 0.0
        avg_ram = 0

    # Get GPU utilization target for this mode
    gpu_target = 0
    gpu_target_met = False
    if GPU_MONITORING_AVAILABLE:
        threshold = UTILIZATION_THRESHOLDS.get(mode, UTILIZATION_THRESHOLDS.get('mask', {}))
        gpu_target = threshold.get('min', 0)
        gpu_target_met = avg_gpu_util >= gpu_target

    summary = BenchmarkSummary(
        test_id=f"{mode.upper()}-{bits}",
        mode=mode,
        bits=bits,
        iterations=iterations,
        avg_throughput_mkeys=avg_throughput,
        min_throughput_mkeys=min_throughput,
        max_throughput_mkeys=max_throughput,
        avg_time_sec=avg_time,
        success_rate=len(successful) / iterations if iterations > 0 else 0,
        avg_gpu_util=avg_gpu_util,
        min_gpu_util=min_gpu_util,
        max_gpu_util=max_gpu_util,
        avg_vram_mb=avg_vram,
        gpu_util_target=gpu_target,
        gpu_util_target_met=gpu_target_met,
        avg_cpu_percent=avg_cpu,
        avg_ram_mb=avg_ram
    )

    # Load baseline and compare
    baselines = load_baselines()
    baseline_key = f"{mode}_{bits}bit"
    if baseline_key in baselines:
        baseline = baselines[baseline_key]
        baseline_throughput = baseline.get("throughput_mkeys", baseline.get("throughput_gkeys", 0) * 1000)
        summary.baseline_throughput = baseline_throughput

        if baseline_throughput > 0 and avg_throughput > 0:
            diff_pct = ((avg_throughput - baseline_throughput) / baseline_throughput) * 100
            summary.baseline_diff_pct = diff_pct

            if diff_pct < -30:
                summary.status = "CRITICAL"
            elif diff_pct < -15:
                summary.status = "WARNING"
            else:
                summary.status = "PASS"

    # Print summary
    print(f"\n  Summary: {avg_throughput:.1f} Mkey/s avg ({min_throughput:.1f}-{max_throughput:.1f})")
    print(f"  Avg time: {avg_time:.3f}s, Success rate: {summary.success_rate*100:.0f}%")
    if avg_gpu_util > 0:
        target_status = "OK" if gpu_target_met else "LOW"
        print(f"  GPU util: {avg_gpu_util:.1f}% avg ({min_gpu_util:.0f}-{max_gpu_util:.0f}%), target: {gpu_target}% [{target_status}]")
        if avg_vram > 0:
            print(f"  VRAM: {avg_vram} MB")
    if summary.baseline_diff_pct is not None:
        sign = "+" if summary.baseline_diff_pct >= 0 else ""
        print(f"  Baseline diff: {sign}{summary.baseline_diff_pct:.1f}% [{summary.status}]")

    return summary


# Benchmark definitions
QUICK_BENCHMARKS = [
    ("mask", 16, "0000"),
    ("mask", 24, "000000"),
    ("sig_ecdsa", 16, "0000"),
    ("taproot", 8, "00"),
    ("txid", 16, "0000"),
]

FULL_BENCHMARKS = [
    ("mask", 16, "0000", 10),
    ("mask", 24, "000000", 5),
    ("mask", 32, "00000000", 3),
    ("sig_ecdsa", 16, "0000", 5),
    ("sig_schnorr", 16, "0000", 5),
    ("taproot", 8, "00", 10),
    ("taproot", 16, "0000", 5),
    ("txid", 16, "0000", 10),
    ("txid", 24, "000000", 3),
]


def run_quick_benchmarks() -> List[BenchmarkSummary]:
    """Run quick benchmark suite."""
    print("\n" + "="*60)
    print("QUICK BENCHMARK SUITE")
    print("="*60)

    summaries = []
    for mode, bits, target in QUICK_BENCHMARKS:
        summary = run_benchmark_iterations(mode, bits, target, 3)
        summaries.append(summary)

    return summaries


def run_full_benchmarks() -> List[BenchmarkSummary]:
    """Run full benchmark suite."""
    print("\n" + "="*60)
    print("FULL BENCHMARK SUITE")
    print("="*60)

    summaries = []
    for item in FULL_BENCHMARKS:
        if len(item) == 4:
            mode, bits, target, iterations = item
        else:
            mode, bits, target = item
            iterations = 5
        summary = run_benchmark_iterations(mode, bits, target, iterations)
        summaries.append(summary)

    return summaries


def run_single_mode(mode: str, bits: int = 16, iterations: int = 3) -> BenchmarkSummary:
    """Run benchmark for a single mode."""
    targets = {
        8: "00",
        16: "0000",
        24: "000000",
        32: "00000000",
    }
    target = targets.get(bits, "0000")
    return run_benchmark_iterations(mode, bits, target, iterations)


def print_final_report(summaries: List[BenchmarkSummary], gpu_name: str):
    """Print final benchmark report with resource monitoring."""
    print("\n" + "="*90)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*90)
    print(f"GPU: {gpu_name}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("-"*90)
    print(f"{'Test':<16} {'Throughput':>14} {'Time':>8} {'GPU%':>8} {'VRAM':>10} {'Status':>8}")
    print("-"*90)

    passed = warnings = failed = 0

    for s in summaries:
        throughput_str = f"{s.avg_throughput_mkeys:.1f} Mkey/s"
        if s.avg_throughput_mkeys >= 1000:
            throughput_str = f"{s.avg_throughput_mkeys/1000:.2f} Gkey/s"

        time_str = f"{s.avg_time_sec:.3f}s"

        gpu_str = f"{s.avg_gpu_util:.0f}%" if s.avg_gpu_util > 0 else "-"
        vram_str = f"{s.avg_vram_mb} MB" if s.avg_vram_mb > 0 else "-"

        status_icon = {"PASS": "[OK]", "WARNING": "[!]", "CRITICAL": "[X]"}.get(s.status, "[ ]")

        print(f"{s.test_id:<16} {throughput_str:>14} {time_str:>8} {gpu_str:>8} {vram_str:>10} {status_icon:>8}")

        if s.status == "PASS":
            passed += 1
        elif s.status == "WARNING":
            warnings += 1
        else:
            failed += 1

    print("-"*90)
    print(f"Total: {len(summaries)} tests | Passed: {passed} | Warnings: {warnings} | Failed: {failed}")

    # Print GPU utilization summary
    gpu_util_results = [s for s in summaries if s.avg_gpu_util > 0]
    if gpu_util_results:
        gpu_ok = sum(1 for s in gpu_util_results if s.gpu_util_target_met)
        gpu_low = len(gpu_util_results) - gpu_ok
        print(f"GPU Utilization: {gpu_ok} met target, {gpu_low} below target")

    if failed > 0:
        print("\n*** CRITICAL REGRESSIONS DETECTED ***")
        return False
    elif warnings > 0:
        print("\n*** WARNINGS: Performance may have degraded ***")
        return True
    else:
        print("\n*** ALL BENCHMARKS PASSED ***")
        return True


def save_results(summaries: List[BenchmarkSummary], gpu_name: str, suite_name: str):
    """Save benchmark results to JSON file."""
    results = {
        "suite": suite_name,
        "timestamp": datetime.now().isoformat(),
        "gpu": gpu_name,
        "results": [asdict(s) for s in summaries],
        "summary": {
            "passed": sum(1 for s in summaries if s.status == "PASS"),
            "warnings": sum(1 for s in summaries if s.status == "WARNING"),
            "failed": sum(1 for s in summaries if s.status == "CRITICAL"),
        }
    }

    output_file = SCRIPT_DIR / f"benchmark_results_{suite_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="VanityMask Benchmark Suite")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmarks (~5 min)")
    parser.add_argument("--full", action="store_true", help="Run full benchmarks (~30 min)")
    parser.add_argument("--mode", type=str, help="Run single mode (mask, sig_ecdsa, sig_schnorr, taproot, txid)")
    parser.add_argument("--bits", type=int, default=16, help="Difficulty in bits (default: 16)")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations (default: 3)")
    parser.add_argument("--save-baseline", action="store_true", help="Save results as new baseline")

    args = parser.parse_args()

    # Check VanitySearch exists
    if not VANITYSEARCH_EXE.exists():
        print(f"ERROR: VanitySearch not found at {VANITYSEARCH_EXE}")
        print("Please build the project first.")
        sys.exit(1)

    gpu_name = get_gpu_info()
    print(f"VanityMask Benchmark Suite")
    print(f"GPU: {gpu_name}")
    print(f"Executable: {VANITYSEARCH_EXE}")

    summaries = []
    suite_name = "custom"

    if args.quick:
        suite_name = "quick"
        summaries = run_quick_benchmarks()
    elif args.full:
        suite_name = "full"
        summaries = run_full_benchmarks()
    elif args.mode:
        suite_name = f"single_{args.mode}"
        summary = run_single_mode(args.mode, args.bits, args.iterations)
        summaries = [summary]
    else:
        # Default to quick
        suite_name = "quick"
        summaries = run_quick_benchmarks()

    # Print and save results
    success = print_final_report(summaries, gpu_name)
    save_results(summaries, gpu_name, suite_name)

    # Optionally save as baseline
    if args.save_baseline:
        baselines = load_baselines()
        for s in summaries:
            key = f"{s.mode}_{s.bits}bit"
            baselines[key] = {
                "throughput_mkeys": s.avg_throughput_mkeys,
                "time_sec": s.avg_time_sec,
                "gpu": gpu_name,
                "timestamp": datetime.now().isoformat()
            }
        save_baselines(baselines)
        print(f"\nBaselines updated in {BASELINES_FILE}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
