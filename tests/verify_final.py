#!/usr/bin/env python3
"""Verify the taproot key found by VanitySearch."""
import hashlib
from ecdsa import SECP256k1

def tagged_hash(tag: bytes, data: bytes) -> bytes:
    """BIP-340 tagged hash: SHA256(SHA256(tag) || SHA256(tag) || data)"""
    tag_hash = hashlib.sha256(tag).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()

# Key found by VanitySearch
d_hex = "A4210AD32FEA0A8C1D8B11F63886A835FE5D0C00BAC883E7FFBA9C876C00D2EC"
d = int(d_hex, 16)

# Compute P = d * G
G = SECP256k1.generator
P = d * G

# Get P.x as bytes (32 bytes, big endian)
P_x = P.x()
P_x_bytes = P_x.to_bytes(32, 'big')
print(f"d (private key): {d_hex}")
print(f"P.x (internal):  {P_x_bytes.hex().upper()}")

# Compute t = TapTweak(P.x)
t_bytes = tagged_hash(b"TapTweak", P_x_bytes)
t = int.from_bytes(t_bytes, 'big') % SECP256k1.order
print(f"t (tweak):       {t_bytes.hex().upper()}")

# Compute Q = P + t*G
tG = t * G
Q = P + tG
Q_x = Q.x()
Q_x_bytes = Q_x.to_bytes(32, 'big')
print(f"Q.x (output):    {Q_x_bytes.hex().upper()}")

# Check if Q.x starts with 0000
if Q_x_bytes[:2] == b'\x00\x00':
    print("\nSUCCESS: Q.x starts with 0000 (matches 16-bit prefix)")
else:
    print(f"\nFAILED: Q.x starts with {Q_x_bytes[:2].hex().upper()}")
