#!/usr/bin/env python3
"""
Verify taproot key computation matches GPU output.
Tests: P.x, TapTweak hash, Q.x
"""
import hashlib
from ecdsa import SECP256k1

def tagged_hash(tag: bytes, data: bytes) -> bytes:
    """BIP-340 tagged hash: SHA256(SHA256(tag) || SHA256(tag) || data)"""
    tag_hash = hashlib.sha256(tag).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()

def verify_taproot_key(privkey_hex: str):
    """Verify taproot key computation for a given private key."""
    print(f"=== Verifying Taproot Key ===")
    print(f"Private key (d): {privkey_hex}")

    # Parse private key
    d = int(privkey_hex, 16)

    # Compute P = d * G
    G = SECP256k1.generator
    P = d * G
    P_x = P.x()
    P_y = P.y()

    P_x_bytes = P_x.to_bytes(32, 'big')
    print(f"P.x = {P_x_bytes.hex().upper()}")
    print(f"P.x MSB (64 bits) = {P_x_bytes[:8].hex().upper()}")

    # Compute t = TapTweak(P.x)
    t_bytes = tagged_hash(b"TapTweak", P_x_bytes)
    t = int.from_bytes(t_bytes, 'big') % SECP256k1.order
    print(f"t (TapTweak) = {t_bytes.hex().upper()}")

    # Compute t*G
    tG = t * G
    print(f"t*G.x = {tG.x().to_bytes(32, 'big').hex().upper()}")

    # Compute Q = P + t*G
    Q = P + tG
    Q_x_bytes = Q.x().to_bytes(32, 'big')
    print(f"Q.x = {Q_x_bytes.hex().upper()}")
    print(f"Q.x MSB (64 bits) = {Q_x_bytes[:8].hex().upper()}")

    # Check if Q.x starts with 00
    if Q_x_bytes[0] == 0:
        print(f"\nQ.x starts with 00: YES (matches 8-bit prefix)")
    else:
        print(f"\nQ.x starts with 00: NO (byte 0 = {Q_x_bytes[0]:02X})")

    return {
        'd': d,
        'P_x': P_x_bytes.hex().upper(),
        't': t_bytes.hex().upper(),
        'Q_x': Q_x_bytes.hex().upper()
    }

if __name__ == "__main__":
    # Use the private key from the latest VanitySearch output
    privkey = "9AAE19AEB99743CB99A25B3E73062089F6067F949DE5034EB2790978F998DBD9"

    result = verify_taproot_key(privkey)

    print("\n=== Comparison with VanitySearch Output ===")
    print("VanitySearch reported:")
    print("  Internal key (P.x):  A3C45A9265B9E3F0BECCCA1423E66A81649D1C1FD99045E0CCBB0BE7A53A1358")
    print("  Tweak (t):           7DD4EE8664E792478B93C964B17688FCB34E45E27CE26BD54973B35795205A3B")
    print("  Output key (Q.x):    651C2ABFD83FE317984BB3AC8A7D1481C7352CF77D86E62F9DEE097AE3F85148")

    print("\nPython computed:")
    print(f"  Internal key (P.x):  {result['P_x']}")
    print(f"  Tweak (t):           {result['t']}")
    print(f"  Output key (Q.x):    {result['Q_x']}")

    # Check if they match
    vs_px = "A3C45A9265B9E3F0BECCCA1423E66A81649D1C1FD99045E0CCBB0BE7A53A1358"
    vs_t = "7DD4EE8664E792478B93C964B17688FCB34E45E27CE26BD54973B35795205A3B"
    vs_qx = "651C2ABFD83FE317984BB3AC8A7D1481C7352CF77D86E62F9DEE097AE3F85148"

    print(f"\nP.x match: {'YES' if result['P_x'] == vs_px else 'NO'}")
    print(f"t match: {'YES' if result['t'] == vs_t else 'NO'}")
    print(f"Q.x match: {'YES' if result['Q_x'] == vs_qx else 'NO'}")
