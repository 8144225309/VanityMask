/*
 * StegoTarget.h - Steganography target/mask structures for Obscurity
 * 
 * This file is part of the Obscurity fork of VanitySearch.
 * NEW FILE - drop into VanitySearch directory
 */

#ifndef STEGOTARGET_H
#define STEGOTARGET_H

#include <cstdint>
#include <cstring>
#include <cstdio>
#include <string>

// Search modes (extends existing VanitySearch modes)
#define SEARCH_COMPRESSED    0
#define SEARCH_UNCOMPRESSED  1
#define SEARCH_BOTH          2
#define SEARCH_STEGO         3   // Steganography mode - match raw X coordinate

// Steganography target structure
typedef struct {
    uint64_t value[4];    // Target value (256 bits = 4 x 64-bit, little-endian)
    uint64_t mask[4];     // Bitmask (1=check, 0=ignore)
    int numBits;          // Number of bits to match (for difficulty display)
} StegoTarget;

// Helper: Convert hex char to int
inline int hexCharToInt(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

// Parse hex string to uint64_t array (big-endian input, little-endian limbs output)
inline int parseHexToLimbs(const char* hex, uint64_t* limbs) {
    memset(limbs, 0, 4 * sizeof(uint64_t));
    if (!hex) return 0;
    
    size_t len = strlen(hex);
    if (len == 0) return 0;
    if (len > 64) len = 64;
    
    int bytesParsed = 0;
    
    // Process from right to left
    for (int i = (int)len - 1; i >= 0; i -= 2) {
        int lo, hi;
        if (i == 0) {
            hi = 0;
            lo = hexCharToInt(hex[0]);
        } else {
            hi = hexCharToInt(hex[i - 1]);
            lo = hexCharToInt(hex[i]);
        }
        if (hi < 0 || lo < 0) return -1;
        
        uint8_t byte = (hi << 4) | lo;
        int limb = bytesParsed / 8;
        int byteInLimb = bytesParsed % 8;
        if (limb < 4) {
            limbs[limb] |= ((uint64_t)byte << (byteInLimb * 8));
        }
        bytesParsed++;
        if (i == 0 && len % 2 == 1) break;
    }
    return bytesParsed;
}

// Generate prefix mask (first N bytes)
inline void generatePrefixMask(uint64_t* mask, int numBytes) {
    memset(mask, 0, 4 * sizeof(uint64_t));
    if (numBytes <= 0 || numBytes > 32) return;
    
    for (int i = 0; i < numBytes; i++) {
        int pos = 31 - i;  // Start from MSB
        int limb = pos / 8;
        int byteInLimb = pos % 8;
        mask[limb] |= ((uint64_t)0xFF << (byteInLimb * 8));
    }
}

// Count bits in mask
inline int countMaskBits(const uint64_t* mask) {
    int count = 0;
    for (int i = 0; i < 4; i++) {
        uint64_t m = mask[i];
        while (m) { count++; m &= m - 1; }
    }
    return count;
}

// Format limbs as hex string
inline void limbsToHex(const uint64_t* limbs, char* out) {
    int pos = 0;
    for (int i = 3; i >= 0; i--) {
        for (int b = 7; b >= 0; b--) {
            sprintf(out + pos, "%02x", (int)((limbs[i] >> (b * 8)) & 0xFF));
            pos += 2;
        }
    }
    out[64] = '\0';
}

#endif // STEGOTARGET_H
