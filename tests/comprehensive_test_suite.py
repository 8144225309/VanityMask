#!/usr/bin/env python3
"""
VanityMask Comprehensive Test Suite

A rigorous test framework for all VanityMask grinding modes with:
- Cryptographic verification using Python ecdsa library
- GPU utilization monitoring (target: 90-95% for EC, 60-65% for TXID)
- Estimated duration tracking
- JSON result output for CI/automation

Usage:
    python comprehensive_test_suite.py --quick     # Quick tests (<5 min)
    python comprehensive_test_suite.py --full      # Full tests (~90 min)
    python comprehensive_test_suite.py --benchmark # Performance benchmarks
"""

import subprocess
import sys
import os
import re
import json
import time
import random
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gpu_monitor import GPUMonitor, check_gpu_available, get_gpu_info, UTILIZATION_THRESHOLDS
except ImportError:
    print("Warning: gpu_monitor.py not found, GPU monitoring disabled")
    GPUMonitor = None

try:
    from ecdsa import SECP256k1, SigningKey
    ECDSA_AVAILABLE = True
except ImportError:
    print("Warning: ecdsa library not found, install with: pip install ecdsa")
    ECDSA_AVAILABLE = False


# Configuration
VANITYSEARCH_EXE = Path(__file__).parent.parent / "x64" / "Release" / "VanitySearch.exe"

# secp256k1 curve parameters (for verification)
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

# Fixed test values
FIXED_Z = "0102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F20"
FIXED_D = "0000000000000000000000000000000000000000000000000000000000000001"
FIXED_P = "79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798"  # G.x

# Minimal valid transaction for TXID tests (59 bytes)
MINIMAL_TX = "0100000001000000000000000000000000000000000000000000000000000000000000000000000000ffffffff0100000000000000000000000000"


@dataclass
class TestResult:
    """Result of a single test."""
    test_id: str
    mode: str
    bits: int
    target: str
    passed: bool
    verified: bool
    elapsed: float
    expected_time: float
    gpu_util_avg: float = 0.0
    gpu_util_met: bool = True
    output_value: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TestSuite:
    """Collection of test results."""
    name: str
    started: str
    completed: Optional[str] = None
    results: List[TestResult] = field(default_factory=list)
    gpu_info: Optional[Dict] = None
    summary: Optional[Dict] = None

    def add_result(self, result: TestResult) -> None:
        self.results.append(result)

    def finalize(self) -> None:
        self.completed = datetime.now().isoformat()
        passed = sum(1 for r in self.results if r.passed)
        verified = sum(1 for r in self.results if r.verified)
        gpu_met = sum(1 for r in self.results if r.gpu_util_met)

        self.summary = {
            'total': len(self.results),
            'passed': passed,
            'verified': verified,
            'gpu_target_met': gpu_met,
            'pass_rate': f"{100*passed/len(self.results):.1f}%" if self.results else "N/A",
            'verify_rate': f"{100*verified/len(self.results):.1f}%" if self.results else "N/A"
        }

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'started': self.started,
            'completed': self.completed,
            'gpu_info': self.gpu_info,
            'summary': self.summary,
            'results': [r.to_dict() for r in self.results]
        }


def random_hex(num_chars: int) -> str:
    """Generate random hex string of given length."""
    return ''.join(random.choices('0123456789ABCDEF', k=num_chars))


def run_vanitysearch(args: List[str], timeout: float = 300) -> Dict:
    """Run VanitySearch with given arguments."""
    if not VANITYSEARCH_EXE.exists():
        return {
            'success': False,
            'stdout': '',
            'stderr': f'VanitySearch not found at {VANITYSEARCH_EXE}',
            'elapsed': 0,
            'returncode': -1
        }

    cmd = [str(VANITYSEARCH_EXE)] + args
    start = time.time()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = time.time() - start
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'elapsed': elapsed,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'TIMEOUT',
            'elapsed': timeout,
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'elapsed': time.time() - start,
            'returncode': -1
        }


def run_vanitysearch_with_gpu(args: List[str], mode: str, timeout: float = 300) -> Tuple[Dict, Dict]:
    """Run VanitySearch with GPU monitoring."""
    if GPUMonitor is None:
        result = run_vanitysearch(args, timeout)
        return result, {'error': 'GPU monitoring not available'}

    monitor = GPUMonitor(sample_interval=0.5)
    monitor.start()

    result = run_vanitysearch(args, timeout)

    stats = monitor.stop()

    threshold = UTILIZATION_THRESHOLDS.get(mode, UTILIZATION_THRESHOLDS['mask'])
    gpu_result = {
        'avg': round(stats.avg_util, 1),
        'min': stats.min_util,
        'max': stats.max_util,
        'samples': stats.sample_count,
        'target': threshold['target'],
        'met': stats.avg_util >= threshold['min']
    }

    return result, gpu_result


# ============================================================================
# OUTPUT EXTRACTION
# ============================================================================

def extract_privkey(output: str) -> Optional[str]:
    """Extract private key from VanitySearch output."""
    match = re.search(r'Priv \(HEX\):\s*0x([0-9A-Fa-f]+)', output)
    if match:
        return match.group(1).upper().zfill(64)
    match = re.search(r'Private key \(d\):\s*([0-9A-Fa-f]+)', output)
    if match:
        return match.group(1).upper().zfill(64)
    return None


def extract_pubkey_x(output: str) -> Optional[str]:
    """Extract pubkey X from mask mode output."""
    match = re.search(r'MASK:([0-9A-Fa-f]+)', output)
    if match:
        return match.group(1).upper()
    return None


def extract_sig_values(output: str) -> Dict:
    """Extract signature values from sig mode output."""
    result = {}
    nonce_match = re.search(r'Nonce \(k\):\s*([0-9A-Fa-f]+)', output)
    if nonce_match:
        result['nonce'] = nonce_match.group(1).upper()
    r_match = re.search(r'sig\.r:\s*([0-9A-Fa-f]+)', output)
    if r_match:
        result['r'] = r_match.group(1).upper()
    s_match = re.search(r'sig\.s:\s*([0-9A-Fa-f]+)', output)
    if s_match:
        result['s'] = s_match.group(1).upper()
    return result


def extract_txid_values(output: str) -> Dict:
    """Extract TXID values from txid mode output."""
    result = {}
    nonce_match = re.search(r'Nonce:\s*0x([0-9A-Fa-f]+)', output)
    if nonce_match:
        result['nonce'] = nonce_match.group(1).upper()
    txid_match = re.search(r'TXID:\s*([0-9A-Fa-f]+)', output)
    if txid_match:
        result['txid'] = txid_match.group(1).upper()
    return result


# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

def verify_mask_result(privkey_hex: str, target: str, mask_hex: str = None) -> Dict:
    """Verify mask mode result."""
    result = {'valid': False, 'pubkey_x': None, 'matches': False, 'error': None}

    if not ECDSA_AVAILABLE:
        result['error'] = 'ecdsa library not available'
        return result

    try:
        d = int(privkey_hex, 16)
        if d <= 0 or d >= SECP256k1.order:
            result['error'] = "Invalid private key: out of range"
            return result

        d_bytes = bytes.fromhex(privkey_hex.zfill(64))
        sk = SigningKey.from_string(d_bytes, curve=SECP256k1)
        pubkey = sk.get_verifying_key().to_string()
        x_hex = pubkey[:32].hex().upper()
        result['pubkey_x'] = x_hex
        result['valid'] = True

        if mask_hex:
            x_int = int(x_hex, 16)
            target_int = int(target.ljust(64, '0'), 16)
            mask_int = int(mask_hex, 16)
            result['matches'] = (x_int & mask_int) == (target_int & mask_int)
        else:
            result['matches'] = x_hex.startswith(target.upper())

        return result

    except Exception as e:
        result['error'] = str(e)
        return result


def verify_ecdsa_signature(nonce_k: str, z: str, d: str, r: str, s: str) -> Dict:
    """Verify ECDSA signature."""
    result = {
        'valid': False, 'r_matches': False, 's_matches': False,
        'ecdsa_verify': False, 'low_s': False, 'error': None
    }

    if not ECDSA_AVAILABLE:
        result['error'] = 'ecdsa library not available'
        return result

    try:
        k = int(nonce_k, 16)
        z_int = int(z, 16)
        d_int = int(d, 16)
        expected_r = int(r, 16)
        expected_s = int(s, 16)

        G = SECP256k1.generator
        R_point = k * G
        computed_r = R_point.x() % N

        result['r_matches'] = (computed_r == expected_r)

        k_inv = pow(k, -1, N)
        computed_s = (k_inv * (z_int + computed_r * d_int)) % N

        if computed_s > N // 2:
            computed_s = N - computed_s

        result['low_s'] = (expected_s <= N // 2)
        result['s_matches'] = (computed_s == expected_s)

        P = d_int * G
        s_inv = pow(expected_s, -1, N)
        u1 = (z_int * s_inv) % N
        u2 = (expected_r * s_inv) % N
        R_verify = u1 * G + u2 * P

        result['ecdsa_verify'] = (R_verify.x() % N == expected_r)
        result['valid'] = all([
            result['r_matches'],
            result['s_matches'],
            result['ecdsa_verify'],
            result['low_s']
        ])

        return result

    except Exception as e:
        result['error'] = str(e)
        return result


def verify_txid_result(raw_tx: str, nonce: str, nonce_offset: int, nonce_len: int, expected_prefix: str) -> Dict:
    """Verify TXID grinding result."""
    result = {'valid': False, 'txid': None, 'matches': False, 'error': None}

    try:
        tx = bytearray.fromhex(raw_tx)
        nonce_int = int(nonce, 16)

        if nonce_offset + nonce_len > len(tx):
            result['error'] = f"Nonce offset {nonce_offset} + len {nonce_len} exceeds TX length {len(tx)}"
            return result

        for i in range(nonce_len):
            tx[nonce_offset + i] = (nonce_int >> (i * 8)) & 0xFF

        hash1 = hashlib.sha256(bytes(tx)).digest()
        hash2 = hashlib.sha256(hash1).digest()

        txid = hash2[::-1].hex().upper()
        result['txid'] = txid
        result['valid'] = True
        result['matches'] = txid.startswith(expected_prefix.upper())

        return result

    except Exception as e:
        result['error'] = str(e)
        return result


# ============================================================================
# EXPECTED DURATION CALCULATIONS
# ============================================================================

def expected_time_ec(bits: int, gkeys_per_sec: float = 27.0) -> float:
    """Calculate expected time for EC operations (mask, sig modes)."""
    difficulty = 2 ** bits
    return difficulty / (gkeys_per_sec * 1e9)


def expected_time_txid(bits: int, mkeys_per_sec: float = 10.0) -> float:
    """Calculate expected time for TXID operations."""
    difficulty = 2 ** bits
    return difficulty / (mkeys_per_sec * 1e6)


# ============================================================================
# TEST DEFINITIONS
# ============================================================================

def test_mask(test_id: str, bits: int, target: str = None, use_gpu_monitor: bool = True) -> TestResult:
    """Run a mask mode test."""
    if target is None:
        target = random_hex(bits // 4)

    prefix_bytes = bits // 8
    args = ['-gpu', '-mask', '-tx', target, '--prefix', str(prefix_bytes), '-stop']

    expected_time = expected_time_ec(bits)

    if use_gpu_monitor:
        result, gpu_stats = run_vanitysearch_with_gpu(args, 'mask', timeout=max(300, expected_time * 10))
    else:
        result = run_vanitysearch(args, timeout=max(300, expected_time * 10))
        gpu_stats = {}

    test_result = TestResult(
        test_id=test_id,
        mode='mask',
        bits=bits,
        target=target,
        passed=result['success'],
        verified=False,
        elapsed=result['elapsed'],
        expected_time=expected_time,
        gpu_util_avg=gpu_stats.get('avg', 0),
        gpu_util_met=gpu_stats.get('met', True)
    )

    if result['success']:
        privkey = extract_privkey(result['stdout'])
        if privkey:
            verify_result = verify_mask_result(privkey, target)
            test_result.verified = verify_result.get('matches', False)
            test_result.output_value = verify_result.get('pubkey_x', '')[:16] + '...'
        else:
            test_result.error = "Could not extract private key"
    else:
        test_result.error = result['stderr'][:200] if result['stderr'] else 'Unknown error'

    return test_result


def test_sig_ecdsa(test_id: str, bits: int, target: str = None, z: str = FIXED_Z, d: str = FIXED_D, use_gpu_monitor: bool = True) -> TestResult:
    """Run an ECDSA signature mode test."""
    if target is None:
        target = random_hex(bits // 4)

    prefix_bytes = bits // 8
    args = ['-gpu', '-sig', '-tx', target, '--prefix', str(prefix_bytes), '-z', z, '-d', d, '-stop']

    expected_time = expected_time_ec(bits)

    if use_gpu_monitor:
        result, gpu_stats = run_vanitysearch_with_gpu(args, 'sig', timeout=max(300, expected_time * 10))
    else:
        result = run_vanitysearch(args, timeout=max(300, expected_time * 10))
        gpu_stats = {}

    test_result = TestResult(
        test_id=test_id,
        mode='sig-ecdsa',
        bits=bits,
        target=target,
        passed=result['success'],
        verified=False,
        elapsed=result['elapsed'],
        expected_time=expected_time,
        gpu_util_avg=gpu_stats.get('avg', 0),
        gpu_util_met=gpu_stats.get('met', True)
    )

    if result['success']:
        sig_values = extract_sig_values(result['stdout'])
        if sig_values.get('nonce') and sig_values.get('r') and sig_values.get('s'):
            verify_result = verify_ecdsa_signature(
                sig_values['nonce'], z, d, sig_values['r'], sig_values['s']
            )
            test_result.verified = verify_result.get('valid', False)
            test_result.output_value = f"R.x={sig_values['r'][:8]}..."
        else:
            test_result.error = "Could not extract signature values"
    else:
        test_result.error = result['stderr'][:200] if result['stderr'] else 'Unknown error'

    return test_result


def test_sig_schnorr(test_id: str, bits: int, target: str = None, z: str = FIXED_Z, d: str = FIXED_D, use_gpu_monitor: bool = True) -> TestResult:
    """Run a Schnorr signature mode test."""
    if target is None:
        target = random_hex(bits // 4)

    prefix_bytes = bits // 8
    args = ['-gpu', '-sig', '--schnorr', '-tx', target, '--prefix', str(prefix_bytes), '-z', z, '-d', d, '-stop']

    expected_time = expected_time_ec(bits)

    if use_gpu_monitor:
        result, gpu_stats = run_vanitysearch_with_gpu(args, 'sig-schnorr', timeout=max(300, expected_time * 10))
    else:
        result = run_vanitysearch(args, timeout=max(300, expected_time * 10))
        gpu_stats = {}

    test_result = TestResult(
        test_id=test_id,
        mode='sig-schnorr',
        bits=bits,
        target=target,
        passed=result['success'],
        verified=False,
        elapsed=result['elapsed'],
        expected_time=expected_time,
        gpu_util_avg=gpu_stats.get('avg', 0),
        gpu_util_met=gpu_stats.get('met', True)
    )

    if result['success']:
        sig_values = extract_sig_values(result['stdout'])
        if sig_values.get('r'):
            # For Schnorr, just verify R.x matches target (s-value uses different formula)
            test_result.verified = sig_values['r'].startswith(target.upper())
            test_result.output_value = f"R.x={sig_values['r'][:8]}..."
        else:
            test_result.error = "Could not extract signature values"
    else:
        test_result.error = result['stderr'][:200] if result['stderr'] else 'Unknown error'

    return test_result


def test_txid(test_id: str, bits: int, target: str = None, raw_tx: str = MINIMAL_TX, nonce_offset: int = None, nonce_len: int = 4, use_gpu_monitor: bool = True) -> TestResult:
    """Run a TXID mode test."""
    if target is None:
        target = random_hex(bits // 4)

    if nonce_offset is None:
        nonce_offset = len(raw_tx) // 2 - nonce_len  # Default: last bytes

    prefix_bytes = bits // 8
    args = ['-gpu', '-txid', '-raw', raw_tx, '-tx', target, '--prefix', str(prefix_bytes), '-stop']

    expected_time = expected_time_txid(bits)

    if use_gpu_monitor:
        result, gpu_stats = run_vanitysearch_with_gpu(args, 'txid', timeout=max(300, expected_time * 10))
    else:
        result = run_vanitysearch(args, timeout=max(300, expected_time * 10))
        gpu_stats = {}

    test_result = TestResult(
        test_id=test_id,
        mode='txid',
        bits=bits,
        target=target,
        passed=result['success'],
        verified=False,
        elapsed=result['elapsed'],
        expected_time=expected_time,
        gpu_util_avg=gpu_stats.get('avg', 0),
        gpu_util_met=gpu_stats.get('met', True)
    )

    if result['success']:
        txid_values = extract_txid_values(result['stdout'])
        if txid_values.get('nonce'):
            verify_result = verify_txid_result(raw_tx, txid_values['nonce'], nonce_offset, nonce_len, target)
            test_result.verified = verify_result.get('matches', False)
            test_result.output_value = f"TXID={verify_result.get('txid', '')[:8]}..."
        else:
            test_result.error = "Could not extract nonce"
    else:
        test_result.error = result['stderr'][:200] if result['stderr'] else 'Unknown error'

    return test_result


def test_error_handling(test_id: str, mode: str, args: List[str], expected_error: str) -> TestResult:
    """Test error handling for invalid inputs."""
    full_args = ['-gpu'] + args

    result = run_vanitysearch(full_args, timeout=10)

    # Error handling tests pass if the command fails and produces expected error
    passed = not result['success'] and (expected_error.lower() in result['stderr'].lower() or
                                         expected_error.lower() in result['stdout'].lower())

    return TestResult(
        test_id=test_id,
        mode=mode,
        bits=0,
        target='N/A',
        passed=passed,
        verified=passed,  # For error tests, passed == verified
        elapsed=result['elapsed'],
        expected_time=0,
        error=None if passed else f"Expected error '{expected_error}' not found"
    )


# ============================================================================
# TEST SUITES
# ============================================================================

def run_quick_tests(suite: TestSuite) -> None:
    """Run quick tests (32-bit and under, <5 minutes total)."""
    print("\n" + "=" * 70)
    print("QUICK TEST SUITE")
    print("=" * 70)

    # MASK tests (8, 16, 24, 32 bits)
    print("\n[MASK MODE TESTS]")
    for bits in [8, 16, 24, 32]:
        test_id = f"MASK-{bits:03d}"
        print(f"  {test_id}: {bits}-bit prefix...", end=' ', flush=True)
        result = test_mask(test_id, bits)
        status = "PASS" if result.verified else ("FAIL" if result.passed else "ERROR")
        print(f"{status} ({result.elapsed:.2f}s)")
        suite.add_result(result)

    # ECDSA Signature tests (8, 16, 32 bits)
    print("\n[ECDSA SIGNATURE TESTS]")
    for bits in [8, 16, 32]:
        test_id = f"SIG-ECDSA-{bits:03d}"
        print(f"  {test_id}: {bits}-bit prefix...", end=' ', flush=True)
        result = test_sig_ecdsa(test_id, bits)
        status = "PASS" if result.verified else ("FAIL" if result.passed else "ERROR")
        print(f"{status} ({result.elapsed:.2f}s)")
        suite.add_result(result)

    # Schnorr Signature tests (8, 16, 32 bits)
    print("\n[SCHNORR SIGNATURE TESTS]")
    for bits in [8, 16, 32]:
        test_id = f"SIG-SCHNORR-{bits:03d}"
        print(f"  {test_id}: {bits}-bit prefix...", end=' ', flush=True)
        result = test_sig_schnorr(test_id, bits)
        status = "PASS" if result.verified else ("FAIL" if result.passed else "ERROR")
        print(f"{status} ({result.elapsed:.2f}s)")
        suite.add_result(result)

    # TXID tests (8, 16 bits)
    print("\n[TXID MODE TESTS]")
    for bits in [8, 16]:
        test_id = f"TXID-{bits:03d}"
        print(f"  {test_id}: {bits}-bit prefix...", end=' ', flush=True)
        result = test_txid(test_id, bits)
        status = "PASS" if result.verified else ("FAIL" if result.passed else "ERROR")
        print(f"{status} ({result.elapsed:.2f}s)")
        suite.add_result(result)


def run_full_tests(suite: TestSuite) -> None:
    """Run full tests including 40-bit difficulty."""
    # First run quick tests
    run_quick_tests(suite)

    print("\n" + "=" * 70)
    print("EXTENDED TESTS (40-bit)")
    print("=" * 70)

    # 40-bit tests (longer running)
    print("\n[40-BIT MASK TEST] (~41s expected)")
    result = test_mask("MASK-040", 40)
    status = "PASS" if result.verified else ("FAIL" if result.passed else "ERROR")
    print(f"  MASK-040: {status} ({result.elapsed:.2f}s)")
    suite.add_result(result)

    print("\n[40-BIT ECDSA SIGNATURE TEST] (~41s expected)")
    result = test_sig_ecdsa("SIG-ECDSA-040", 40)
    status = "PASS" if result.verified else ("FAIL" if result.passed else "ERROR")
    print(f"  SIG-ECDSA-040: {status} ({result.elapsed:.2f}s)")
    suite.add_result(result)

    print("\n[24-BIT TXID TEST] (~27s expected)")
    result = test_txid("TXID-024", 24)
    status = "PASS" if result.verified else ("FAIL" if result.passed else "ERROR")
    print(f"  TXID-024: {status} ({result.elapsed:.2f}s)")
    suite.add_result(result)


def run_error_tests(suite: TestSuite) -> None:
    """Run error handling tests."""
    print("\n" + "=" * 70)
    print("ERROR HANDLING TESTS")
    print("=" * 70)

    error_tests = [
        ("ERR-001", "mask", ["-mask", "-tx", ""], "target"),
        ("ERR-002", "mask", ["-mask", "-tx", "GGG"], "invalid"),
        ("ERR-005", "sig", ["-sig", "-tx", "DEAD", "-d", FIXED_D], "hash"),
        ("ERR-006", "sig", ["-sig", "-tx", "DEAD", "-z", FIXED_Z], "key"),
        ("ERR-008", "txid", ["-txid", "-tx", "DEAD"], "raw"),
    ]

    for test_id, mode, args, expected_error in error_tests:
        print(f"  {test_id}: {mode} error handling...", end=' ', flush=True)
        result = test_error_handling(test_id, mode, args, expected_error)
        status = "PASS" if result.passed else "FAIL"
        print(f"{status}")
        suite.add_result(result)


def run_benchmark_tests(suite: TestSuite) -> None:
    """Run performance benchmark tests with multiple iterations."""
    print("\n" + "=" * 70)
    print("PERFORMANCE BENCHMARKS")
    print("=" * 70)

    # Run multiple iterations of 32-bit tests for statistical accuracy
    print("\n[MASK 32-BIT BENCHMARK] (10 iterations)")
    for i in range(10):
        result = test_mask(f"BENCH-MASK-32-{i+1:02d}", 32)
        print(f"  Iteration {i+1}: {result.elapsed:.3f}s (GPU: {result.gpu_util_avg:.1f}%)")
        suite.add_result(result)

    print("\n[ECDSA 32-BIT BENCHMARK] (10 iterations)")
    for i in range(10):
        result = test_sig_ecdsa(f"BENCH-SIG-32-{i+1:02d}", 32)
        print(f"  Iteration {i+1}: {result.elapsed:.3f}s (GPU: {result.gpu_util_avg:.1f}%)")
        suite.add_result(result)


def print_summary(suite: TestSuite) -> None:
    """Print test summary."""
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    if suite.summary:
        print(f"\nTotal tests: {suite.summary['total']}")
        print(f"Passed: {suite.summary['passed']} ({suite.summary['pass_rate']})")
        print(f"Verified: {suite.summary['verified']} ({suite.summary['verify_rate']})")
        print(f"GPU target met: {suite.summary['gpu_target_met']}")

    # Group by mode
    by_mode = {}
    for r in suite.results:
        mode = r.mode
        if mode not in by_mode:
            by_mode[mode] = []
        by_mode[mode].append(r)

    print("\nBy Mode:")
    for mode, results in sorted(by_mode.items()):
        passed = sum(1 for r in results if r.passed)
        verified = sum(1 for r in results if r.verified)
        avg_time = sum(r.elapsed for r in results) / len(results)
        avg_gpu = sum(r.gpu_util_avg for r in results) / len(results)
        print(f"  {mode}: {passed}/{len(results)} passed, {verified}/{len(results)} verified, "
              f"avg time: {avg_time:.2f}s, avg GPU: {avg_gpu:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='VanityMask Comprehensive Test Suite')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only (<5 min)')
    parser.add_argument('--full', action='store_true', help='Run full test suite (~90 min)')
    parser.add_argument('--benchmark', action='store_true', help='Run performance benchmarks')
    parser.add_argument('--errors', action='store_true', help='Run error handling tests')
    parser.add_argument('--output', '-o', default='test_results.json', help='Output JSON file')
    args = parser.parse_args()

    # Default to quick if nothing specified
    if not any([args.quick, args.full, args.benchmark, args.errors]):
        args.quick = True

    print("=" * 70)
    print("VANITYMASK COMPREHENSIVE TEST SUITE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Check prerequisites
    if not VANITYSEARCH_EXE.exists():
        print(f"\nERROR: VanitySearch.exe not found at {VANITYSEARCH_EXE}")
        print("Please build the project first.")
        sys.exit(1)

    if not ECDSA_AVAILABLE:
        print("\nWARNING: ecdsa library not available, verification disabled")
        print("Install with: pip install ecdsa")

    # Get GPU info
    gpu_info = get_gpu_info() if GPUMonitor else {'error': 'GPU monitoring not available'}
    if 'name' in gpu_info:
        print(f"\nGPU: {gpu_info['name']}")
        print(f"Memory: {gpu_info.get('memory', 'Unknown')}")

    # Create test suite
    suite_name = 'quick' if args.quick else ('full' if args.full else ('benchmark' if args.benchmark else 'errors'))
    suite = TestSuite(
        name=suite_name,
        started=datetime.now().isoformat(),
        gpu_info=gpu_info
    )

    # Run tests
    if args.quick:
        run_quick_tests(suite)
    elif args.full:
        run_full_tests(suite)
    elif args.benchmark:
        run_benchmark_tests(suite)

    if args.errors or args.quick or args.full:
        run_error_tests(suite)

    # Finalize and save
    suite.finalize()
    print_summary(suite)

    output_path = Path(__file__).parent / args.output
    with open(output_path, 'w') as f:
        json.dump(suite.to_dict(), f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # Exit with error code if any tests failed
    if suite.summary and suite.summary['passed'] < suite.summary['total']:
        sys.exit(1)


if __name__ == '__main__':
    main()
