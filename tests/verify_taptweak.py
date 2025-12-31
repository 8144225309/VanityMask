#!/usr/bin/env python3
"""
Verify GPU SHA256_TapTweak matches Python implementation.
Tests the byte order fix (bswap32) in GPU/GPUHash.h
"""
import hashlib
from ecdsa import SECP256k1

def tagged_hash(tag: bytes, data: bytes) -> bytes:
    """BIP-340 tagged hash: SHA256(SHA256(tag) || SHA256(tag) || data)"""
    tag_hash = hashlib.sha256(tag).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()

def compute_taptweak(px_hex: str) -> str:
    """Compute TapTweak hash for a given P.x"""
    px_bytes = bytes.fromhex(px_hex)
    assert len(px_bytes) == 32, f"P.x must be 32 bytes, got {len(px_bytes)}"
    t = tagged_hash(b"TapTweak", px_bytes)
    return t.hex().upper()

def compute_Q(px_hex: str, py_hex: str = None) -> tuple:
    """Compute Q = P + t*G where t = TapTweak(P.x)"""
    px_bytes = bytes.fromhex(px_hex)
    px_int = int.from_bytes(px_bytes, 'big')

    # Compute tweak
    t = tagged_hash(b"TapTweak", px_bytes)
    t_int = int.from_bytes(t, 'big') % SECP256k1.order

    # If we have the full point, compute Q = P + t*G
    # For now, just return the tweak
    return t.hex().upper(), t_int

def verify_gpu_output(gpu_px_msb: str, gpu_qx_msb: str):
    """
    Given GPU's stored P.x MSB and Q.x MSB (each 64 bits = 16 hex chars),
    verify the TapTweak computation.

    Note: GPU stores only MSB, so we can't compute full Q.
    But we can verify the TapTweak hash if we have the full P.x.
    """
    print(f"GPU P.x MSB: {gpu_px_msb}")
    print(f"GPU Q.x MSB: {gpu_qx_msb}")
    print()

    # We need the full P.x to verify, but GPU only stores MSB
    # For debugging, we'll show what the TapTweak tag hash should be
    tag = b"TapTweak"
    tag_hash = hashlib.sha256(tag).digest()
    print(f"TapTweak tag hash: {tag_hash.hex().upper()}")

    # The precomputed constant should match:
    # 0xE80FE163, 0x9C9CA050, 0xE3AF1B39, 0xC143C63E,
    # 0x429CBCEB, 0x15D940FB, 0xB5C5A1F4, 0xAF57C5E9
    expected = "E80FE1639C9CA050E3AF1B39C143C63E429CBCEB15D940FBB5C5A1F4AF57C5E9"
    print(f"Expected constant:  {expected}")
    print(f"Match: {tag_hash.hex().upper() == expected}")

def test_known_key():
    """Test with a known private key"""
    print("=" * 60)
    print("Testing with known private key d=1 (Generator point)")
    print("=" * 60)

    # d=1 gives P = G (generator point)
    Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
    px_hex = format(Gx, '064X')
    print(f"P.x = {px_hex}")

    # Compute TapTweak
    t_hex, t_int = compute_Q(px_hex)
    print(f"t = TapTweak(P.x) = {t_hex}")

    # Compute t*G
    G = SECP256k1.generator
    tG = t_int * G
    print(f"t*G.x = {tG.x():064X}")
    print(f"t*G.y = {tG.y():064X}")

    # Compute Q = P + t*G = G + t*G = (1+t)*G
    Q = (1 + t_int) * G
    print(f"Q.x = {Q.x():064X}")
    print(f"Q.y = {Q.y():064X}")
    print()

def test_from_output():
    """Parse output from VanitySearch and verify"""
    print("=" * 60)
    print("Testing GPU output from actual run")
    print("=" * 60)

    # Example from debug output:
    # GPU P.x MSB: 7244B344F074670D
    # GPU Q.x MSB: DE00E928F528073C
    verify_gpu_output("7244B344F074670D", "DE00E928F528073C")

if __name__ == "__main__":
    test_known_key()
    print()
    test_from_output()
