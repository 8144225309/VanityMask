#!/usr/bin/env python3
"""
GPU Monitoring Module for VanityMask Tests

Monitors GPU utilization during test execution to ensure
the GPU is being saturated (target: 90-95% for EC ops, 60-65% for TXID).
"""

import subprocess
import threading
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class GPUStats:
    """Statistics from GPU monitoring session."""
    min_util: float = 0.0
    max_util: float = 0.0
    avg_util: float = 0.0
    samples: List[int] = field(default_factory=list)
    sample_count: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None

    @property
    def target_met_ec(self) -> bool:
        """Check if EC operation target (90%+) was met."""
        return self.avg_util >= 90.0

    @property
    def target_met_txid(self) -> bool:
        """Check if TXID operation target (55%+) was met."""
        return self.avg_util >= 55.0

    def to_dict(self) -> Dict:
        return {
            'min': self.min_util,
            'max': self.max_util,
            'avg': round(self.avg_util, 2),
            'samples': self.sample_count,
            'duration_seconds': round(self.duration_seconds, 2),
            'target_met_ec': self.target_met_ec,
            'target_met_txid': self.target_met_txid,
            'error': self.error
        }


class GPUMonitor:
    """
    Monitor GPU utilization in a background thread.

    Usage:
        monitor = GPUMonitor()
        monitor.start()
        # ... run GPU workload ...
        stats = monitor.stop()
        print(f"Average GPU: {stats.avg_util}%")
    """

    def __init__(self, sample_interval: float = 0.5, gpu_id: int = 0):
        """
        Initialize GPU monitor.

        Args:
            sample_interval: Time between samples in seconds
            gpu_id: GPU index to monitor (default: 0)
        """
        self.sample_interval = sample_interval
        self.gpu_id = gpu_id
        self._samples: List[int] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: float = 0.0
        self._error: Optional[str] = None

    def start(self) -> None:
        """Start monitoring GPU utilization in background thread."""
        if self._running:
            return

        self._samples = []
        self._error = None
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> GPUStats:
        """
        Stop monitoring and return statistics.

        Returns:
            GPUStats with min/max/avg utilization and sample data
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

        duration = time.time() - self._start_time

        if self._error:
            return GPUStats(error=self._error, duration_seconds=duration)

        if not self._samples:
            return GPUStats(error="No samples collected", duration_seconds=duration)

        return GPUStats(
            min_util=min(self._samples),
            max_util=max(self._samples),
            avg_util=sum(self._samples) / len(self._samples),
            samples=self._samples.copy(),
            sample_count=len(self._samples),
            duration_seconds=duration
        )

    def _sample_loop(self) -> None:
        """Background thread that samples GPU utilization."""
        while self._running:
            try:
                result = subprocess.run(
                    [
                        'nvidia-smi',
                        f'--id={self.gpu_id}',
                        '--query-gpu=utilization.gpu',
                        '--format=csv,noheader,nounits'
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2.0
                )

                if result.returncode == 0:
                    util_str = result.stdout.strip()
                    if util_str.isdigit():
                        self._samples.append(int(util_str))
                else:
                    self._error = f"nvidia-smi failed: {result.stderr}"

            except subprocess.TimeoutExpired:
                self._error = "nvidia-smi timeout"
            except FileNotFoundError:
                self._error = "nvidia-smi not found"
            except Exception as e:
                self._error = str(e)

            time.sleep(self.sample_interval)


def get_gpu_info() -> Dict:
    """
    Get GPU information.

    Returns:
        Dict with GPU name, memory, driver version, etc.
    """
    try:
        result = subprocess.run(
            [
                'nvidia-smi',
                '--query-gpu=name,memory.total,driver_version,cuda_version',
                '--format=csv,noheader'
            ],
            capture_output=True,
            text=True,
            timeout=5.0
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            if len(parts) >= 4:
                return {
                    'name': parts[0],
                    'memory': parts[1],
                    'driver': parts[2],
                    'cuda': parts[3]
                }
        return {'error': result.stderr}

    except Exception as e:
        return {'error': str(e)}


def check_gpu_available() -> bool:
    """Check if nvidia-smi is available and a GPU is present."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '-L'],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        return result.returncode == 0 and 'GPU' in result.stdout
    except:
        return False


def run_with_monitoring(cmd: List[str], expected_util: int = 90, timeout: float = 300) -> Dict:
    """
    Run a command while monitoring GPU utilization.

    Args:
        cmd: Command to run as list of strings
        expected_util: Expected GPU utilization percentage
        timeout: Command timeout in seconds

    Returns:
        Dict with command result and GPU stats
    """
    monitor = GPUMonitor()
    monitor.start()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        success = result.returncode == 0
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        success = False
        stdout = ""
        stderr = "TIMEOUT"
    except Exception as e:
        success = False
        stdout = ""
        stderr = str(e)

    gpu_stats = monitor.stop()

    return {
        'command': ' '.join(cmd),
        'success': success,
        'stdout': stdout,
        'stderr': stderr,
        'gpu_stats': gpu_stats.to_dict(),
        'gpu_target_met': gpu_stats.avg_util >= expected_util
    }


# Expected utilization thresholds by mode
UTILIZATION_THRESHOLDS = {
    'mask': {'min': 85, 'target': 95, 'description': 'EC operations (compute-bound)'},
    'sig': {'min': 85, 'target': 95, 'description': 'EC operations (compute-bound)'},
    'sig-schnorr': {'min': 85, 'target': 95, 'description': 'EC operations (compute-bound)'},
    'txid': {'min': 50, 'target': 62, 'description': 'SHA256 operations (memory-bound)'},
    'vanity': {'min': 85, 'target': 95, 'description': 'EC + hash operations'},
}


def check_utilization(mode: str, stats: GPUStats) -> Dict:
    """
    Check if GPU utilization meets threshold for given mode.

    Args:
        mode: Grinding mode (mask, sig, txid, etc.)
        stats: GPUStats from monitoring session

    Returns:
        Dict with pass/fail status and details
    """
    threshold = UTILIZATION_THRESHOLDS.get(mode, UTILIZATION_THRESHOLDS['mask'])

    return {
        'mode': mode,
        'avg_util': stats.avg_util,
        'min_threshold': threshold['min'],
        'target_threshold': threshold['target'],
        'meets_min': stats.avg_util >= threshold['min'],
        'meets_target': stats.avg_util >= threshold['target'],
        'description': threshold['description']
    }


if __name__ == '__main__':
    # Self-test
    print("GPU Monitor Self-Test")
    print("=" * 50)

    if not check_gpu_available():
        print("ERROR: No GPU available or nvidia-smi not found")
        exit(1)

    info = get_gpu_info()
    print(f"GPU: {info.get('name', 'Unknown')}")
    print(f"Memory: {info.get('memory', 'Unknown')}")
    print(f"Driver: {info.get('driver', 'Unknown')}")
    print(f"CUDA: {info.get('cuda', 'Unknown')}")
    print()

    print("Testing monitor (5 seconds)...")
    monitor = GPUMonitor(sample_interval=0.5)
    monitor.start()
    time.sleep(5)
    stats = monitor.stop()

    print(f"Samples collected: {stats.sample_count}")
    print(f"Min utilization: {stats.min_util}%")
    print(f"Max utilization: {stats.max_util}%")
    print(f"Avg utilization: {stats.avg_util:.1f}%")
    print(f"Duration: {stats.duration_seconds:.1f}s")

    if stats.error:
        print(f"Error: {stats.error}")

    print("\nSelf-test complete!")
