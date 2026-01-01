#!/usr/bin/env python3
"""
Verify GPU taproot computation against Python implementation.
Compares P.x, tweak hash, t*G, and Q values.
"""
import hashlib
from ecdsa import SECP256k1

def tagged_hash(tag: bytes, data: bytes) -> bytes:
    """BIP-340 tagged hash: SHA256(SHA256(tag) || SHA256(tag) || data)"""
    tag_hash = hashlib.sha256(tag).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()

def verify_gpu_match(px_hex: str, gpu_tweak_hex: str, gpu_tgx_hex: str, gpu_qx_hex: str):
    """Verify GPU computed values against Python implementation."""
    print("=" * 70)
    print("VERIFYING GPU TAPROOT COMPUTATION")
    print("=" * 70)

    # Parse P.x (convert GPU's space-separated format to bytes)
    px_hex_clean = px_hex.replace(" ", "")
    px_bytes = bytes.fromhex(px_hex_clean)
    px_int = int.from_bytes(px_bytes, 'big')
    print(f"\nP.x (from GPU): {px_hex_clean}")

    # Compute TapTweak hash in Python
    python_tweak = tagged_hash(b"TapTweak", px_bytes)
    python_tweak_hex = python_tweak.hex().upper()
    print(f"\nTweak hash:")
    print(f"  GPU:    {gpu_tweak_hex.replace(' ', '')}")
    print(f"  Python: {python_tweak_hex}")
    print(f"  Match:  {'YES' if gpu_tweak_hex.replace(' ', '') == python_tweak_hex else 'NO'}")

    # Compute t*G in Python
    t_int = int.from_bytes(python_tweak, 'big') % SECP256k1.order
    G = SECP256k1.generator
    tG = t_int * G
    python_tgx_hex = format(tG.x(), '064X')
    print(f"\nt*G.x:")
    print(f"  GPU:    {gpu_tgx_hex.replace(' ', '')}")
    print(f"  Python: {python_tgx_hex}")
    print(f"  Match:  {'YES' if gpu_tgx_hex.replace(' ', '') == python_tgx_hex else 'NO'}")

    # To compute Q, we need P (both x and y)
    # We only have P.x from GPU, so we can lift the y-coordinate
    # There are 2 possible y values - we'll try both
    p = SECP256k1.curve.p()
    y_squared = (pow(px_int, 3, p) + 7) % p

    # Check if y_squared is a quadratic residue
    y = pow(y_squared, (p + 1) // 4, p)
    if pow(y, 2, p) != y_squared:
        print("\nERROR: P.x is not on the secp256k1 curve!")
        return

    # Try both y values
    y1 = y
    y2 = p - y

    from ecdsa.ellipticcurve import Point
    curve = SECP256k1.curve

    for i, y_val in enumerate([y1, y2]):
        P = Point(curve, px_int, y_val)
        Q = P + tG
        qx_hex = format(Q.x(), '064X')
        print(f"\nQ.x (with y{'_even' if y_val == y1 else '_odd'}):")
        print(f"  GPU:    {gpu_qx_hex.replace(' ', '')}")
        print(f"  Python: {qx_hex}")
        if gpu_qx_hex.replace(' ', '') == qx_hex:
            print(f"  Match:  YES (P.y = {'even' if y_val == y1 else 'odd'})")
        else:
            print(f"  Match:  NO")

if __name__ == "__main__":
    # Values from latest test (tid=6619)
    # GPU TAPROOT DEBUG (tid=6619):
    #   P.x:    A984034525915842 5BF98FB0F019AFDD 8A44068101E93D60 4575EC8D01F11908
    #   tweak:  BABF1B4A6F2DBEEE 2EE91F1A556258A9 BF9B3B81031CEDDF 90A6700C8A0897F7
    #   t*G.x:  67E6ABEC346EBEC5 BA2C90070F936A31 C23AE76F4BBA188A 0035269E1FAFD6FF
    #   Q.x:    0000959D41FA2E5A 0B219E2BD175F4FE E77FFC9FC3D1700D 3C0684E550DD9C82

    verify_gpu_match(
        px_hex="A984034525915842 5BF98FB0F019AFDD 8A44068101E93D60 4575EC8D01F11908",
        gpu_tweak_hex="BABF1B4A6F2DBEEE 2EE91F1A556258A9 BF9B3B81031CEDDF 90A6700C8A0897F7",
        gpu_tgx_hex="67E6ABEC346EBEC5 BA2C90070F936A31 C23AE76F4BBA188A 0035269E1FAFD6FF",
        gpu_qx_hex="0000959D41FA2E5A 0B219E2BD175F4FE E77FFC9FC3D1700D 3C0684E550DD9C82"
    )
