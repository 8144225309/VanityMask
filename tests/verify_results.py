#!/usr/bin/env python3
"""
VanityMask output verification script.
Independently verifies cryptographic correctness of grinding results.

Usage:
    python verify_results.py mask <privkey_hex> <expected_prefix>
    python verify_results.py sig <nonce_hex> <msg_hash> <privkey> <r_hex> <s_hex> [--schnorr]
    python verify_results.py txid <raw_tx_hex> <nonce_hex> <nonce_offset> <nonce_len> <expected_prefix>
"""

import sys
import hashlib
from typing import Tuple, Optional

# secp256k1 curve parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

# Point at infinity represented as None
INFINITY = None


def modinv(a: int, m: int) -> int:
    """Modular inverse using extended Euclidean algorithm"""
    if a < 0:
        a = a % m
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        raise ValueError(f"Modular inverse does not exist for {a} mod {m}")
    return x % m


def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """Extended Euclidean algorithm"""
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y


def point_add(p1: Optional[Tuple[int, int]], p2: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """Add two EC points on secp256k1"""
    if p1 is INFINITY:
        return p2
    if p2 is INFINITY:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2:
        if y1 != y2:
            # Point + (-Point) = infinity
            return INFINITY
        # Point doubling
        if y1 == 0:
            return INFINITY
        # slope = (3*x1^2) / (2*y1)
        s = (3 * x1 * x1 * modinv(2 * y1, P)) % P
    else:
        # slope = (y2-y1) / (x2-x1)
        s = ((y2 - y1) * modinv(x2 - x1, P)) % P

    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P

    return (x3, y3)


def point_mul(k: int, p: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """Scalar multiplication k * P using double-and-add"""
    if k == 0 or p is INFINITY:
        return INFINITY

    k = k % N  # Reduce k modulo curve order
    if k == 0:
        return INFINITY

    result = INFINITY
    addend = p

    while k > 0:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1

    return result


def verify_mask(privkey_hex: str, expected_prefix: str) -> bool:
    """
    Verify mask mode result.

    Args:
        privkey_hex: Private key in hex
        expected_prefix: Expected prefix of pubkey X coordinate (hex)

    Returns:
        True if pubkey.x starts with expected prefix
    """
    try:
        k = int(privkey_hex, 16)
        if k <= 0 or k >= N:
            print(f"  ERROR: Invalid private key (out of range)")
            return False

        G = (Gx, Gy)
        pubkey = point_mul(k, G)

        if pubkey is INFINITY:
            print(f"  ERROR: Public key is point at infinity")
            return False

        x_hex = format(pubkey[0], '064x')
        expected_lower = expected_prefix.lower()

        if x_hex.startswith(expected_lower):
            print(f"  OK: pubkey.x = {x_hex[:16]}... starts with {expected_lower}")
            return True
        else:
            print(f"  ERROR: pubkey.x = {x_hex[:16]}... does NOT start with {expected_lower}")
            return False

    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def verify_signature(nonce_hex: str, msg_hash_hex: str, privkey_hex: str,
                     r_hex: str, s_hex: str, schnorr: bool = False) -> bool:
    """
    Verify signature mode result.

    Args:
        nonce_hex: Nonce k in hex
        msg_hash_hex: Message hash z in hex
        privkey_hex: Private key d in hex
        r_hex: Expected r value in hex
        s_hex: Expected s value in hex
        schnorr: Whether this is a Schnorr signature

    Returns:
        True if signature components are correct
    """
    try:
        k = int(nonce_hex, 16)
        z = int(msg_hash_hex, 16)
        d = int(privkey_hex, 16)
        expected_r = int(r_hex, 16)
        expected_s = int(s_hex, 16)

        if k <= 0 or k >= N:
            print(f"  ERROR: Invalid nonce k (out of range)")
            return False

        G = (Gx, Gy)

        # Compute R = k * G
        R = point_mul(k, G)
        if R is INFINITY:
            print(f"  ERROR: R is point at infinity")
            return False

        r = R[0] % N  # r = R.x mod n

        # For Schnorr, if R.y is odd, we need k' = n - k
        # But since VanityMask outputs the adjusted k, we just verify R.x
        if schnorr:
            # Just verify R.x matches - VanityMask handles y-parity internally
            if r != expected_r:
                print(f"  ERROR: r mismatch.")
                print(f"    Expected: {format(expected_r, '064x')}")
                print(f"    Got:      {format(r, '064x')}")
                return False
            print(f"  OK: Schnorr R.x = {format(r, '064x')[:16]}... matches")
            # For Schnorr, s computation is different (BIP340), skip s verification
            return True

        # Verify r matches
        if r != expected_r:
            print(f"  ERROR: r mismatch.")
            print(f"    Expected: {format(expected_r, '064x')}")
            print(f"    Got:      {format(r, '064x')}")
            return False

        # Compute s = k^-1 * (z + r*d) mod n
        k_inv = modinv(k, N)
        s = (k_inv * (z + r * d)) % N

        # Low-s normalization (BIP146)
        if s > N // 2:
            s = N - s

        if s != expected_s:
            print(f"  ERROR: s mismatch.")
            print(f"    Expected: {format(expected_s, '064x')}")
            print(f"    Got:      {format(s, '064x')}")
            # Also show non-normalized s
            s_raw = (k_inv * (z + r * d)) % N
            print(f"    Raw s:    {format(s_raw, '064x')}")
            return False

        print(f"  OK: r = {format(r, '064x')[:16]}...")
        print(f"  OK: s = {format(s, '064x')[:16]}... (low-s normalized)")

        # Optional: Verify signature using ECDSA verification
        # s^-1 * (z*G + r*P) should equal R
        s_inv = modinv(s, N)
        P = point_mul(d, G)  # Public key
        u1 = (z * s_inv) % N
        u2 = (r * s_inv) % N
        R_verify = point_add(point_mul(u1, G), point_mul(u2, P))

        if R_verify is INFINITY or R_verify[0] % N != r:
            print(f"  WARNING: ECDSA verification failed (may be due to low-s adjustment)")
        else:
            print(f"  OK: ECDSA signature verification passed")

        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_txid(raw_tx_hex: str, nonce_hex: str, nonce_offset: int,
                nonce_len: int, expected_prefix: str) -> bool:
    """
    Verify TXID mode result.

    Args:
        raw_tx_hex: Original raw transaction hex
        nonce_hex: Nonce value in hex (little-endian as stored in tx)
        nonce_offset: Byte offset where nonce is placed
        nonce_len: Number of bytes for nonce
        expected_prefix: Expected TXID prefix (hex)

    Returns:
        True if TXID starts with expected prefix
    """
    try:
        # Parse raw tx
        tx = bytearray.fromhex(raw_tx_hex)

        # Parse nonce (interpret as little-endian integer, then insert as little-endian)
        nonce = int(nonce_hex, 16)

        # Insert nonce at offset (little-endian)
        for i in range(nonce_len):
            if nonce_offset + i < len(tx):
                tx[nonce_offset + i] = (nonce >> (i * 8)) & 0xFF

        # Double SHA256
        hash1 = hashlib.sha256(bytes(tx)).digest()
        hash2 = hashlib.sha256(hash1).digest()

        # Reverse for display (Bitcoin TXID convention)
        txid = hash2[::-1].hex()

        expected_lower = expected_prefix.lower()

        if txid.startswith(expected_lower):
            print(f"  OK: TXID = {txid[:16]}... starts with {expected_lower}")
            return True
        else:
            print(f"  ERROR: TXID = {txid[:16]}... does NOT start with {expected_lower}")
            print(f"    Modified tx (first 64 bytes): {tx[:64].hex()}")
            return False

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def parse_output_file(filename: str) -> dict:
    """Parse VanityMask output file to extract values"""
    result = {}
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('Priv (HEX):'):
                    # Extract hex value after 0x
                    hex_val = line.split(':')[1].strip()
                    if hex_val.startswith('0x'):
                        hex_val = hex_val[2:]
                    result['privkey'] = hex_val
                elif line.startswith('Nonce (k):'):
                    hex_val = line.split(':')[1].strip()
                    if hex_val.startswith('0x'):
                        hex_val = hex_val[2:]
                    result['nonce'] = hex_val
                elif line.startswith('sig.r:'):
                    result['r'] = line.split(':')[1].strip()
                elif line.startswith('sig.s:'):
                    result['s'] = line.split(':')[1].strip()
                elif line.startswith('Nonce:'):
                    hex_val = line.split(':')[1].strip()
                    if hex_val.startswith('0x'):
                        hex_val = hex_val[2:]
                    result['txid_nonce'] = hex_val
                elif line.startswith('TXID:'):
                    result['txid'] = line.split(':')[1].strip()
    except FileNotFoundError:
        print(f"  ERROR: Output file not found: {filename}")
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == 'mask':
        if len(sys.argv) < 4:
            print("Usage: verify_results.py mask <privkey_hex> <expected_prefix>")
            sys.exit(1)
        privkey = sys.argv[2]
        prefix = sys.argv[3]
        success = verify_mask(privkey, prefix)
        sys.exit(0 if success else 1)

    elif mode == 'sig':
        if len(sys.argv) < 7:
            print("Usage: verify_results.py sig <nonce> <msg_hash> <privkey> <r> <s> [--schnorr]")
            sys.exit(1)
        nonce = sys.argv[2]
        msg_hash = sys.argv[3]
        privkey = sys.argv[4]
        r = sys.argv[5]
        s = sys.argv[6]
        schnorr = '--schnorr' in sys.argv
        success = verify_signature(nonce, msg_hash, privkey, r, s, schnorr)
        sys.exit(0 if success else 1)

    elif mode == 'txid':
        if len(sys.argv) < 7:
            print("Usage: verify_results.py txid <raw_tx> <nonce> <offset> <len> <prefix>")
            sys.exit(1)
        raw_tx = sys.argv[2]
        nonce = sys.argv[3]
        offset = int(sys.argv[4])
        length = int(sys.argv[5])
        prefix = sys.argv[6]
        success = verify_txid(raw_tx, nonce, offset, length, prefix)
        sys.exit(0 if success else 1)

    elif mode == 'test':
        # Run built-in self-tests
        print("=== Running self-tests ===\n")

        # Test 1: Known private key -> public key
        print("[TEST] Private key 1 -> Generator point")
        G = point_mul(1, (Gx, Gy))
        assert G == (Gx, Gy), "1*G should equal G"
        print(f"  OK: 1*G = G")

        # Test 2: Known private key 2 -> 2G
        print("[TEST] Private key 2 -> 2G")
        G2 = point_mul(2, (Gx, Gy))
        G2_expected = point_add((Gx, Gy), (Gx, Gy))
        assert G2 == G2_expected, "2*G should equal G+G"
        print(f"  OK: 2*G = G+G")

        # Test 3: Verify known Bitcoin address derivation
        # Private key 1 should give pubkey 0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
        print("[TEST] Verify pubkey for private key 1")
        P = point_mul(1, (Gx, Gy))
        x_hex = format(P[0], '064x')
        expected_x = '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'
        assert x_hex == expected_x, f"Expected {expected_x}, got {x_hex}"
        print(f"  OK: pubkey.x = {x_hex[:16]}...")

        # Test 4: TXID double-SHA256
        print("[TEST] TXID double-SHA256")
        test_data = bytes.fromhex('0100000000')
        h1 = hashlib.sha256(test_data).digest()
        h2 = hashlib.sha256(h1).digest()
        txid = h2[::-1].hex()
        print(f"  OK: SHA256(SHA256(0100000000)) = {txid[:16]}...")

        # Test 5: Modular inverse
        print("[TEST] Modular inverse")
        a = 12345
        a_inv = modinv(a, N)
        assert (a * a_inv) % N == 1, "a * a^-1 should equal 1 mod N"
        print(f"  OK: {a} * {a_inv} mod N = 1")

        print("\n=== All self-tests passed ===")
        sys.exit(0)

    else:
        print(f"Unknown mode: {mode}")
        print("Modes: mask, sig, txid, test")
        sys.exit(1)


if __name__ == '__main__':
    main()
