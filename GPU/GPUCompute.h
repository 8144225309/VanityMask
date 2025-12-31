/*
 * This file is part of the VanitySearch distribution (https://github.com/JeanLucPons/VanitySearch).
 * Copyright (c) 2019 Jean Luc PONS.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
*/

// CUDA Kernel main function
// Compute SecpK1 keys and calculate RIPEMD160(SHA256(key)) then check prefix
// For the kernel, we use a 16 bits prefix lookup table which correspond to ~3 Base58 characters
// A second level lookup table contains 32 bits prefix (if used)
// (The CPU computes the full address and check the full prefix)
//
// We use affine coordinates for elliptic curve point (ie Z=1)

__device__ __noinline__ void CheckPoint(uint32_t *_h, int32_t incr, int32_t endo, int32_t mode,prefix_t *prefix,
                                        uint32_t *lookup32, uint32_t maxFound, uint32_t *out,int type) {

  uint32_t   off;
  prefixl_t  l32;
  prefix_t   pr0;
  prefix_t   hit;
  uint32_t   pos;
  uint32_t   st;
  uint32_t   ed;
  uint32_t   mi;
  uint32_t   lmi;
  uint32_t   tid = (blockIdx.x*blockDim.x) + threadIdx.x;
  char       add[48];

  if (prefix == NULL) {

    // No lookup compute address and return
    char *pattern = (char *)lookup32;
    _GetAddress(type, _h, add);
    if (_Match(add, pattern)) {
      // found
      goto addItem;
    }

  } else {

    // Lookup table
    pr0 = *(prefix_t *)(_h);
    hit = prefix[pr0];

    if (hit) {

      if (lookup32) {
        off = lookup32[pr0];
        l32 = _h[0];
        st = off;
        ed = off + hit - 1;
        while (st <= ed) {
          mi = (st + ed) / 2;
          lmi = lookup32[mi];
          if (l32 < lmi) {
            ed = mi - 1;
          } else if (l32 == lmi) {
            // found
            goto addItem;
          } else {
            st = mi + 1;
          }
        }
        return;
      }

    addItem:

      pos = atomicAdd(out, 1);
      if (pos < maxFound) {
        out[pos*ITEM_SIZE32 + 1] = tid;
        out[pos*ITEM_SIZE32 + 2] = (uint32_t)(incr << 16) | (uint32_t)(mode << 15) | (uint32_t)(endo);
        out[pos*ITEM_SIZE32 + 3] = _h[0];
        out[pos*ITEM_SIZE32 + 4] = _h[1];
        out[pos*ITEM_SIZE32 + 5] = _h[2];
        out[pos*ITEM_SIZE32 + 6] = _h[3];
        out[pos*ITEM_SIZE32 + 7] = _h[4];
      }

    }

  }

}

// -----------------------------------------------------------------------------------------

#define CHECK_POINT(_h,incr,endo,mode)  CheckPoint(_h,incr,endo,mode,prefix,lookup32,maxFound,out,P2PKH)
#define CHECK_POINT_P2SH(_h,incr,endo,mode)  CheckPoint(_h,incr,endo,mode,prefix,lookup32,maxFound,out,P2SH)

__device__ __noinline__ void CheckHashComp(prefix_t *prefix, uint64_t *px, uint8_t isOdd, int32_t incr,
                                           uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  uint32_t   h[5];
  uint64_t   pe1x[4];
  uint64_t   pe2x[4];

  _GetHash160Comp(px, isOdd, (uint8_t *)h);
  CHECK_POINT(h, incr, 0, true);
  _ModMult(pe1x, px, _beta);
  _GetHash160Comp(pe1x, isOdd, (uint8_t *)h);
  CHECK_POINT(h, incr, 1, true);
  _ModMult(pe2x, px, _beta2);
  _GetHash160Comp(pe2x, isOdd, (uint8_t *)h);
  CHECK_POINT(h, incr, 2, true);

  _GetHash160Comp(px, !isOdd, (uint8_t *)h);
  CHECK_POINT(h, -incr, 0, true);
  _GetHash160Comp(pe1x, !isOdd, (uint8_t *)h);
  CHECK_POINT(h, -incr, 1, true);
  _GetHash160Comp(pe2x, !isOdd, (uint8_t *)h);
  CHECK_POINT(h, -incr, 2, true);


}

__device__ __noinline__ void CheckHashP2SHComp(prefix_t *prefix, uint64_t *px, uint8_t isOdd, int32_t incr,
  uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  uint32_t   h[5];
  uint64_t   pe1x[4];
  uint64_t   pe2x[4];

  _GetHash160P2SHComp(px, isOdd, (uint8_t *)h);
  CHECK_POINT_P2SH(h, incr, 0, true);
  _ModMult(pe1x, px, _beta);
  _GetHash160P2SHComp(pe1x, isOdd, (uint8_t *)h);
  CHECK_POINT_P2SH(h, incr, 1, true);
  _ModMult(pe2x, px, _beta2);
  _GetHash160P2SHComp(pe2x, isOdd, (uint8_t *)h);
  CHECK_POINT_P2SH(h, incr, 2, true);

  _GetHash160P2SHComp(px, !isOdd, (uint8_t *)h);
  CHECK_POINT_P2SH(h, -incr, 0, true);
  _GetHash160P2SHComp(pe1x, !isOdd, (uint8_t *)h);
  CHECK_POINT_P2SH(h, -incr, 1, true);
  _GetHash160P2SHComp(pe2x, !isOdd, (uint8_t *)h);
  CHECK_POINT_P2SH(h, -incr, 2, true);

}

// -----------------------------------------------------------------------------------------

__device__ __noinline__ void CheckHashUncomp(prefix_t *prefix, uint64_t *px, uint64_t *py, int32_t incr,
                                             uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  uint32_t   h[5];
  uint64_t   pe1x[4];
  uint64_t   pe2x[4];
  uint64_t   pyn[4];

  _GetHash160(px, py, (uint8_t *)h);
  CHECK_POINT(h, incr, 0, false);
  _ModMult(pe1x, px, _beta);
  _GetHash160(pe1x, py, (uint8_t *)h);
  CHECK_POINT(h, incr, 1, false);
  _ModMult(pe2x, px, _beta2);
  _GetHash160(pe2x, py, (uint8_t *)h);
  CHECK_POINT(h, incr, 2, false);

  ModNeg256(pyn,py);

  _GetHash160(px, pyn, (uint8_t *)h);
  CHECK_POINT(h, -incr, 0, false);
  _GetHash160(pe1x, pyn, (uint8_t *)h);
  CHECK_POINT(h, -incr, 1, false);
  _GetHash160(pe2x, pyn, (uint8_t *)h);
  CHECK_POINT(h, -incr, 2, false);

}

__device__ __noinline__ void CheckHashP2SHUncomp(prefix_t *prefix, uint64_t *px, uint64_t *py, int32_t incr,
  uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  uint32_t   h[5];
  uint64_t   pe1x[4];
  uint64_t   pe2x[4];
  uint64_t   pyn[4];

  _GetHash160P2SHUncomp(px, py, (uint8_t *)h);
  CHECK_POINT_P2SH(h, incr, 0, false);
  _ModMult(pe1x, px, _beta);
  _GetHash160P2SHUncomp(pe1x, py, (uint8_t *)h);
  CHECK_POINT_P2SH(h, incr, 1, false);
  _ModMult(pe2x, px, _beta2);
  _GetHash160P2SHUncomp(pe2x, py, (uint8_t *)h);
  CHECK_POINT_P2SH(h, incr, 2, false);

  ModNeg256(pyn, py);

  _GetHash160P2SHUncomp(px, pyn, (uint8_t *)h);
  CHECK_POINT_P2SH(h, -incr, 0, false);
  _GetHash160P2SHUncomp(pe1x, pyn, (uint8_t *)h);
  CHECK_POINT_P2SH(h, -incr, 1, false);
  _GetHash160P2SHUncomp(pe2x, pyn, (uint8_t *)h);
  CHECK_POINT_P2SH(h, -incr, 2, false);

}

// -----------------------------------------------------------------------------------------

__device__ __noinline__ void CheckHash(uint32_t mode, prefix_t *prefix, uint64_t *px, uint64_t *py, int32_t incr,
                                       uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  switch (mode) {
  case SEARCH_COMPRESSED:
    CheckHashComp(prefix, px, (uint8_t)(py[0] & 1), incr, lookup32, maxFound, out);
    break;
  case SEARCH_UNCOMPRESSED:
    CheckHashUncomp(prefix, px, py, incr, lookup32, maxFound, out);
    break;
  case SEARCH_BOTH:
    CheckHashComp(prefix, px, (uint8_t)(py[0] & 1), incr, lookup32, maxFound, out);
    CheckHashUncomp(prefix, px, py, incr, lookup32, maxFound, out);
    break;
  }

}

__device__ __noinline__ void CheckP2SHHash(uint32_t mode, prefix_t *prefix, uint64_t *px, uint64_t *py, int32_t incr,
  uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  switch (mode) {
  case SEARCH_COMPRESSED:
    CheckHashP2SHComp(prefix, px, (uint8_t)(py[0] & 1), incr, lookup32, maxFound, out);
    break;
  case SEARCH_UNCOMPRESSED:
    CheckHashP2SHUncomp(prefix, px, py, incr, lookup32, maxFound, out);
    break;
  case SEARCH_BOTH:
    CheckHashP2SHComp(prefix, px, (uint8_t)(py[0] & 1), incr, lookup32, maxFound, out);
    CheckHashP2SHUncomp(prefix, px, py, incr, lookup32, maxFound, out);
    break;
  }

}

#define CHECK_PREFIX(incr) CheckHash(mode, sPrefix, px, py, j*GRP_SIZE + (incr), lookup32, maxFound, out)

// -----------------------------------------------------------------------------------------

__device__ void ComputeKeys(uint32_t mode, uint64_t *startx, uint64_t *starty,
                            prefix_t *sPrefix, uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  uint64_t dx[GRP_SIZE/2+1][4];
  uint64_t px[4];
  uint64_t py[4];
  uint64_t pyn[4];
  uint64_t sx[4];
  uint64_t sy[4];
  uint64_t dy[4];
  uint64_t _s[4];
  uint64_t _p2[4];
  char pattern[48];

  // Load starting key
  __syncthreads();
  Load256A(sx, startx);
  Load256A(sy, starty);
  Load256(px, sx);
  Load256(py, sy);

  if (sPrefix == NULL) {
    memcpy(pattern,lookup32,48);
    lookup32 = (uint32_t *)pattern;
  }

  for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {

    // Fill group with delta x
    uint32_t i;
    for (i = 0; i < HSIZE; i++)
      ModSub256(dx[i], Gx[i], sx);
    ModSub256(dx[i] , Gx[i], sx);  // For the first point
    ModSub256(dx[i+1],_2Gnx, sx);  // For the next center point

    // Compute modular inverse
    _ModInvGrouped(dx);

    // We use the fact that P + i*G and P - i*G has the same deltax, so the same inverse
    // We compute key in the positive and negative way from the center of the group

    // Check starting point
    CHECK_PREFIX(GRP_SIZE / 2);

    ModNeg256(pyn,py);

    for(i = 0; i < HSIZE; i++) {

      // P = StartPoint + i*G
      Load256(px, sx);
      Load256(py, sy);
      ModSub256(dy, Gy[i], py);

      _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
      _ModSqr(_p2, _s);             // _p2 = pow2(s)

      ModSub256(px, _p2,px);
      ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

      ModSub256(py, Gx[i], px);
      _ModMult(py, _s);             // py = - s*(ret.x-p2.x)
      ModSub256(py, Gy[i]);         // py = - p2.y - s*(ret.x-p2.x);

      CHECK_PREFIX(GRP_SIZE / 2 + (i + 1));

      // P = StartPoint - i*G, if (x,y) = i*G then (x,-y) = -i*G
      Load256(px, sx);
      ModSub256(dy,pyn,Gy[i]);

      _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
      _ModSqr(_p2, _s);             // _p = pow2(s)

      ModSub256(px, _p2, px);
      ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

      ModSub256(py, px, Gx[i]);
      _ModMult(py, _s);             // py = s*(ret.x-p2.x)
      ModSub256(py, Gy[i], py);     // py = - p2.y - s*(ret.x-p2.x);

      CHECK_PREFIX(GRP_SIZE / 2 - (i + 1));

    }

    // First point (startP - (GRP_SZIE/2)*G)
    Load256(px, sx);
    Load256(py, sy);
    ModNeg256(dy, Gy[i]);
    ModSub256(dy, py);

    _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
    _ModSqr(_p2,_s);              // _p = pow2(s)

    ModSub256(px, _p2, px);
    ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

    ModSub256(py, px, Gx[i]);
    _ModMult(py, _s);             // py = s*(ret.x-p2.x)
    ModSub256(py, Gy[i], py);     // py = - p2.y - s*(ret.x-p2.x);

    CHECK_PREFIX(0);

    i++;

    // Next start point (startP + GRP_SIZE*G)
    Load256(px, sx);
    Load256(py, sy);
    ModSub256(dy, _2Gny, py);

    _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
    _ModSqr(_p2, _s);             // _p2 = pow2(s)

    ModSub256(px, _p2, px);
    ModSub256(px, _2Gnx);         // px = pow2(s) - p1.x - p2.x;

    ModSub256(py, _2Gnx, px);
    _ModMult(py, _s);             // py = - s*(ret.x-p2.x)
    ModSub256(py, _2Gny);         // py = - p2.y - s*(ret.x-p2.x);

  }

  // Update starting point
  __syncthreads();
  Store256A(startx, px);
  Store256A(starty, py);

}

// -----------------------------------------------------------------------------------------

#define CHECK_PREFIX_P2SH(incr) CheckP2SHHash(mode, sPrefix, px, py, j*GRP_SIZE + (incr), lookup32, maxFound, out)

__device__ void ComputeKeysP2SH(uint32_t mode, uint64_t *startx, uint64_t *starty,
  prefix_t *sPrefix, uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  uint64_t dx[GRP_SIZE / 2 + 1][4];
  uint64_t px[4];
  uint64_t py[4];
  uint64_t pyn[4];
  uint64_t sx[4];
  uint64_t sy[4];
  uint64_t dy[4];
  uint64_t _s[4];
  uint64_t _p2[4];
  char pattern[48];

  // Load starting key
  __syncthreads();
  Load256A(sx, startx);
  Load256A(sy, starty);
  Load256(px, sx);
  Load256(py, sy);

  if (sPrefix == NULL) {
    memcpy(pattern, lookup32, 48);
    lookup32 = (uint32_t *)pattern;
  }

  for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {

    // Fill group with delta x
    uint32_t i;
    for (i = 0; i < HSIZE; i++)
      ModSub256(dx[i], Gx[i], sx);
    ModSub256(dx[i], Gx[i], sx);  // For the first point
    ModSub256(dx[i + 1], _2Gnx, sx);  // For the next center point

    // Compute modular inverse
    _ModInvGrouped(dx);

    // We use the fact that P + i*G and P - i*G has the same deltax, so the same inverse
    // We compute key in the positive and negative way from the center of the group

    // Check starting point
    CHECK_PREFIX_P2SH(GRP_SIZE / 2);

    ModNeg256(pyn, py);

    for (i = 0; i < HSIZE; i++) {

      __syncthreads();
      // P = StartPoint + i*G
      Load256(px, sx);
      Load256(py, sy);
      ModSub256(dy, Gy[i], py);

      _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
      _ModSqr(_p2, _s);             // _p2 = pow2(s)

      ModSub256(px, _p2, px);
      ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

      ModSub256(py, Gx[i], px);
      _ModMult(py, _s);             // py = - s*(ret.x-p2.x)
      ModSub256(py, Gy[i]);         // py = - p2.y - s*(ret.x-p2.x);

      CHECK_PREFIX_P2SH(GRP_SIZE / 2 + (i + 1));

      __syncthreads();
      // P = StartPoint - i*G, if (x,y) = i*G then (x,-y) = -i*G
      Load256(px, sx);
      ModSub256(dy, pyn, Gy[i]);

      _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
      _ModSqr(_p2, _s);             // _p = pow2(s)

      ModSub256(px, _p2, px);
      ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

      ModSub256(py,px, Gx[i]);
      _ModMult(py, _s);             // py = s*(ret.x-p2.x)
      ModSub256(py, Gy[i], py);     // py = - p2.y - s*(ret.x-p2.x);

      CHECK_PREFIX_P2SH(GRP_SIZE / 2 - (i + 1));

    }

    __syncthreads();
    // First point (startP - (GRP_SZIE/2)*G)
    Load256(px, sx);
    Load256(py, sy);
    ModNeg256(dy, Gy[i]);
    ModSub256(dy, py);

    _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
    _ModSqr(_p2, _s);              // _p = pow2(s)

    ModSub256(px, _p2, px);
    ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

    ModSub256(py,px , Gx[i]);
    _ModMult(py, _s);             // py = s*(ret.x-p2.x)
    ModSub256(py, Gy[i], py);     // py = - p2.y - s*(ret.x-p2.x);

    CHECK_PREFIX_P2SH(0);

    i++;

    __syncthreads();
    // Next start point (startP + GRP_SIZE*G)
    Load256(px, sx);
    Load256(py, sy);
    ModSub256(dy, _2Gny, py);

    _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
    _ModSqr(_p2, _s);             // _p2 = pow2(s)

    ModSub256(px, _p2, px);
    ModSub256(px, _2Gnx);         // px = pow2(s) - p1.x - p2.x;

    ModSub256(py, _2Gnx, px);
    _ModMult(py, _s);             // py = - s*(ret.x-p2.x)
    ModSub256(py, _2Gny);         // py = - p2.y - s*(ret.x-p2.x);

  }

  // Update starting point
  __syncthreads();
  Store256A(startx, px);
  Store256A(starty, py);

}

// -----------------------------------------------------------------------------------------
// Optimized kernel for compressed P2PKH address only

#define CHECK_P2PKH_POINT(_incr) {                                             \
_GetHash160CompSym(px, (uint8_t *)h1, (uint8_t *)h2);                          \
CheckPoint(h1, (_incr), 0, true, sPrefix, lookup32, maxFound, out, P2PKH);     \
CheckPoint(h2, -(_incr), 0, true, sPrefix, lookup32, maxFound, out, P2PKH);    \
_ModMult(pe1x, px, _beta);                                                     \
_GetHash160CompSym(pe1x, (uint8_t *)h1, (uint8_t *)h2);                        \
CheckPoint(h1, (_incr), 1, true, sPrefix, lookup32, maxFound, out, P2PKH);     \
CheckPoint(h2, -(_incr), 1, true, sPrefix, lookup32, maxFound, out, P2PKH);    \
_ModMult(pe2x, px, _beta2);                                                    \
_GetHash160CompSym(pe2x, (uint8_t *)h1, (uint8_t *)h2);                        \
CheckPoint(h1, (_incr), 2, true, sPrefix, lookup32, maxFound, out, P2PKH);     \
CheckPoint(h2, -(_incr), 2, true, sPrefix, lookup32, maxFound, out, P2PKH);    \
}

// -----------------------------------------------------------------------------------------
// Steganography mode: match raw X coordinate against target/mask
// No hashing, no endomorphisms - just direct bitmask comparison
// -----------------------------------------------------------------------------------------

__device__ __noinline__ void CheckStegoPoint(uint64_t *px, int32_t incr, uint32_t maxFound, uint32_t *out) {

  uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;

  // Check if (px & mask) == (target & mask)
  // Using constant memory: _stego_value[4] and _stego_mask[4]
  bool match = true;
  for (int i = 0; i < 4; i++) {
    if ((px[i] & _stego_mask[i]) != (_stego_value[i] & _stego_mask[i])) {
      match = false;
      break;
    }
  }

  if (match) {
    uint32_t pos = atomicAdd(out, 1);
    if (pos < maxFound) {
      out[pos * ITEM_SIZE32 + 1] = tid;
      // incr in high 16 bits, mode=1 (compressed) in bit 15, endo=0 in low 15 bits
      out[pos * ITEM_SIZE32 + 2] = (uint32_t)((incr << 16) | (1 << 15) | 0);
      // Store first 160 bits of X coordinate for quick verification
      out[pos * ITEM_SIZE32 + 3] = (uint32_t)(px[0]);
      out[pos * ITEM_SIZE32 + 4] = (uint32_t)(px[0] >> 32);
      out[pos * ITEM_SIZE32 + 5] = (uint32_t)(px[1]);
      out[pos * ITEM_SIZE32 + 6] = (uint32_t)(px[1] >> 32);
      out[pos * ITEM_SIZE32 + 7] = (uint32_t)(px[2]);
    }
  }
}

#define CHECK_STEGO_POINT(_incr) CheckStegoPoint(px, (_incr), maxFound, out)

__device__ void ComputeKeysStego(uint64_t *startx, uint64_t *starty, uint32_t maxFound, uint32_t *out) {

  uint64_t dx[GRP_SIZE/2+1][4];
  uint64_t px[4];
  uint64_t py[4];
  uint64_t pyn[4];
  uint64_t sx[4];
  uint64_t sy[4];
  uint64_t dy[4];
  uint64_t _s[4];
  uint64_t _p2[4];

  // Load starting key
  __syncthreads();
  Load256A(sx, startx);
  Load256A(sy, starty);
  Load256(px, sx);
  Load256(py, sy);

  for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {

    // Fill group with delta x
    uint32_t i;
    for (i = 0; i < HSIZE; i++)
      ModSub256(dx[i], Gx[i], sx);
    ModSub256(dx[i] , Gx[i], sx);  // For the first point
    ModSub256(dx[i+1],_2Gnx, sx);  // For the next center point

    // Compute modular inverse
    _ModInvGrouped(dx);

    // We use the fact that P + i*G and P - i*G has the same deltax, so the same inverse
    // We compute key in the positive and negative way from the center of the group

    // Check starting point (center of group)
    // For stego: both +k and -k give same X coordinate, but we track both for different k values
    CHECK_STEGO_POINT(j*GRP_SIZE + (GRP_SIZE/2));

    ModNeg256(pyn,py);

    for(i = 0; i < HSIZE; i++) {

      __syncthreads();
      // P = StartPoint + i*G
      Load256(px, sx);
      Load256(py, sy);
      ModSub256(dy, Gy[i], py);

      _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
      _ModSqr(_p2, _s);             // _p2 = pow2(s)

      ModSub256(px, _p2,px);
      ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

      CHECK_STEGO_POINT(j*GRP_SIZE + (GRP_SIZE/2 + (i + 1)));

      __syncthreads();
      // P = StartPoint - i*G, if (x,y) = i*G then (x,-y) = -i*G
      Load256(px, sx);
      ModSub256(dy,pyn,Gy[i]);

      _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
      _ModSqr(_p2, _s);             // _p = pow2(s)

      ModSub256(px, _p2, px);
      ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

      CHECK_STEGO_POINT(j*GRP_SIZE + (GRP_SIZE/2 - (i + 1)));

    }

    __syncthreads();
    // First point (startP - (GRP_SIZE/2)*G)
    Load256(px, sx);
    Load256(py, sy);
    ModNeg256(dy, Gy[i]);
    ModSub256(dy, py);

    _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
    _ModSqr(_p2,_s);              // _p = pow2(s)

    ModSub256(px, _p2, px);
    ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

    CHECK_STEGO_POINT(j*GRP_SIZE + (0));

    i++;

    __syncthreads();
    // Next start point (startP + GRP_SIZE*G)
    Load256(px, sx);
    Load256(py, sy);
    ModSub256(dy, _2Gny, py);

    _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
    _ModSqr(_p2, _s);             // _p2 = pow2(s)

    ModSub256(px, _p2, px);
    ModSub256(px, _2Gnx);         // px = pow2(s) - p1.x - p2.x;

    ModSub256(py, _2Gnx, px);
    _ModMult(py, _s);             // py = - s*(ret.x-p2.x)
    ModSub256(py, _2Gny);         // py = - p2.y - s*(ret.x-p2.x);

  }

  // Update starting point
  __syncthreads();
  Store256A(startx, px);
  Store256A(starty, py);

}

// -----------------------------------------------------------------------------------------

__device__ void ComputeKeysComp(uint64_t *startx, uint64_t *starty, prefix_t *sPrefix, uint32_t *lookup32, uint32_t maxFound, uint32_t *out) {

  uint64_t dx[GRP_SIZE/2+1][4];
  uint64_t px[4];
  uint64_t py[4];
  uint64_t pyn[4];
  uint64_t sx[4];
  uint64_t sy[4];
  uint64_t dy[4];
  uint64_t _s[4];
  uint64_t _p2[4];
  uint32_t   h1[5];
  uint32_t   h2[5];
  uint64_t   pe1x[4];
  uint64_t   pe2x[4];

  // Load starting key
  __syncthreads();
  Load256A(sx, startx);
  Load256A(sy, starty);
  Load256(px, sx);
  Load256(py, sy);

  for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {

    // Fill group with delta x
    uint32_t i;
    for (i = 0; i < HSIZE; i++)
      ModSub256(dx[i], Gx[i], sx);
    ModSub256(dx[i] , Gx[i], sx);  // For the first point
    ModSub256(dx[i+1],_2Gnx, sx);  // For the next center point

    // Compute modular inverse
    _ModInvGrouped(dx);

    // We use the fact that P + i*G and P - i*G has the same deltax, so the same inverse
    // We compute key in the positive and negative way from the center of the group

    // Check starting point
    CHECK_P2PKH_POINT(j*GRP_SIZE + (GRP_SIZE/2));

    ModNeg256(pyn,py);

    for(i = 0; i < HSIZE; i++) {

      __syncthreads();
      // P = StartPoint + i*G
      Load256(px, sx);
      Load256(py, sy);
      ModSub256(dy, Gy[i], py);

      _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
      _ModSqr(_p2, _s);             // _p2 = pow2(s)

      ModSub256(px, _p2,px);
      ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

      CHECK_P2PKH_POINT(j*GRP_SIZE + (GRP_SIZE/2 + (i + 1)));

      __syncthreads();
      // P = StartPoint - i*G, if (x,y) = i*G then (x,-y) = -i*G
      Load256(px, sx);
      ModSub256(dy,pyn,Gy[i]);

      _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
      _ModSqr(_p2, _s);             // _p = pow2(s)

      ModSub256(px, _p2, px);
      ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

      CHECK_P2PKH_POINT(j*GRP_SIZE + (GRP_SIZE/2 - (i + 1)));

    }

    __syncthreads();
    // First point (startP - (GRP_SZIE/2)*G)
    Load256(px, sx);
    Load256(py, sy);
    ModNeg256(dy, Gy[i]);
    ModSub256(dy, py);

    _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
    _ModSqr(_p2,_s);              // _p = pow2(s)

    ModSub256(px, _p2, px);
    ModSub256(px, Gx[i]);         // px = pow2(s) - p1.x - p2.x;

    CHECK_P2PKH_POINT(j*GRP_SIZE + (0));

    i++;

    __syncthreads();
    // Next start point (startP + GRP_SIZE*G)
    Load256(px, sx);
    Load256(py, sy);
    ModSub256(dy, _2Gny, py);

    _ModMult(_s, dy, dx[i]);      //  s = (p2.y-p1.y)*inverse(p2.x-p1.x)
    _ModSqr(_p2, _s);             // _p2 = pow2(s)

    ModSub256(px, _p2, px);
    ModSub256(px, _2Gnx);         // px = pow2(s) - p1.x - p2.x;

    ModSub256(py, _2Gnx, px);
    _ModMult(py, _s);             // py = - s*(ret.x-p2.x)
    ModSub256(py, _2Gny);         // py = - p2.y - s*(ret.x-p2.x);

  }

  // Update starting point
  __syncthreads();
  Store256A(startx, px);
  Store256A(starty, py);

}

// -----------------------------------------------------------------------------------------
// TAPROOT MODE: Post-tweak pubkey grinding
// Computes Q = P + hash("TapTweak" || P.x)*G and checks Q.x prefix
// -----------------------------------------------------------------------------------------

// Modular addition: r = a + b mod p (using r = -((-a) - b))
__device__ void ModAdd256(uint64_t* r, uint64_t* a, uint64_t* b) {
  uint64_t neg_a[4], tmp[4];
  ModNeg256(neg_a, a);
  ModSub256(tmp, neg_a, b);
  ModNeg256(r, tmp);
}

// -----------------------------------------------------------------------------------------
// Curve order n for secp256k1 (for scalar reduction)
// n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
// Stored in little-endian limb order: n[0] = LSB, n[3] = MSB
// -----------------------------------------------------------------------------------------
__device__ __constant__ uint64_t SECP256K1_ORDER[4] = {
  0xBFD25E8CD0364141ULL,  // n[0] - least significant
  0xBAAEDCE6AF48A03BULL,  // n[1]
  0xFFFFFFFFFFFFFFFEULL,  // n[2]
  0xFFFFFFFFFFFFFFFFULL   // n[3] - most significant
};

// Compare scalar with curve order n
// Returns: -1 if scalar < n, 0 if scalar == n, 1 if scalar > n
__device__ int CompareWithOrder(uint64_t scalar[4]) {
  // Compare from MSB to LSB
  for (int i = 3; i >= 0; i--) {
    if (scalar[i] > SECP256K1_ORDER[i]) return 1;
    if (scalar[i] < SECP256K1_ORDER[i]) return -1;
  }
  return 0;  // Equal
}

// Subtract curve order: result = scalar - n (assumes scalar >= n)
__device__ void SubtractOrder(uint64_t result[4], uint64_t scalar[4]) {
  uint64_t borrow = 0;
  for (int i = 0; i < 4; i++) {
    uint64_t sub = SECP256K1_ORDER[i] + borrow;
    borrow = (sub < borrow) ? 1 : 0;  // Overflow in adding borrow
    borrow += (scalar[i] < sub) ? 1 : 0;  // Borrow from subtraction
    result[i] = scalar[i] - sub;
  }
}

// Reduce scalar modulo curve order n
// If scalar >= n, computes scalar - n (single subtraction is sufficient since hash < 2n)
__device__ void ModReduceOrder(uint64_t scalar[4]) {
  if (CompareWithOrder(scalar) >= 0) {
    uint64_t reduced[4];
    SubtractOrder(reduced, scalar);
    scalar[0] = reduced[0];
    scalar[1] = reduced[1];
    scalar[2] = reduced[2];
    scalar[3] = reduced[3];
  }
}

// Point doubling in affine coordinates: (Rx, Ry) = 2*(Px, Py)
// IMPORTANT: Handles aliasing (Rx==Px and/or Ry==Py) by using local copies
__device__ void PointDoubleAffine(uint64_t Rx[4], uint64_t Ry[4],
                                  uint64_t Px[4], uint64_t Py[4]) {
  uint64_t s[4], s2[4], tmp[4], num[4];
  uint64_t denom[5];  // _ModInv requires 5-element array (320 bits)
  uint64_t localPx[4], localPy[4];

  // Copy inputs to avoid aliasing issues when Rx==Px or Ry==Py
  Load256(localPx, Px);
  Load256(localPy, Py);

  // s = 3*Px^2 / (2*Py) mod p (a=0 for secp256k1)
  _ModSqr(num, localPx);
  Load256(tmp, num);
  ModAdd256(num, num, tmp);
  ModAdd256(num, num, tmp);      // num = 3*Px^2

  ModAdd256(denom, localPy, localPy);      // denom = 2*Py
  denom[4] = 0;  // Clear 5th element for _ModInv

  // Use proven _ModInv instead of custom chain
  _ModInv(denom);
  _ModMult(s, num, denom);

  // Rx = s^2 - 2*Px
  _ModSqr(s2, s);
  Load256(Rx, s2);
  ModSub256(Rx, localPx);
  ModSub256(Rx, localPx);

  // Ry = s*(Px - Rx) - Py
  ModSub256(tmp, localPx, Rx);
  _ModMult(Ry, s, tmp);
  ModSub256(Ry, localPy);
}

// Point addition in affine coordinates: (Rx, Ry) = (Ax, Ay) + (Bx, By)
// IMPORTANT: Handles aliasing (Rx==Ax, Ry==Ay, etc.) by using local copies
__device__ void PointAddAffine(uint64_t Rx[4], uint64_t Ry[4],
                               uint64_t Ax[4], uint64_t Ay[4],
                               uint64_t Bx[4], uint64_t By[4]) {
  uint64_t dx[5];  // _ModInv requires 5-element array (320 bits)
  uint64_t dy[4], s[4], s2[4];
  uint64_t localAx[4], localAy[4], localBx[4], localBy[4];

  // Copy inputs to avoid aliasing issues
  Load256(localAx, Ax);
  Load256(localAy, Ay);
  Load256(localBx, Bx);
  Load256(localBy, By);

  // s = (By - Ay) / (Bx - Ax) mod p
  ModSub256(dy, localBy, localAy);
  ModSub256(dx, localBx, localAx);
  dx[4] = 0;  // Clear 5th element for _ModInv

  // Use the proven _ModInv instead of custom chain
  _ModInv(dx);
  _ModMult(s, dy, dx);

  // Rx = s^2 - Ax - Bx
  _ModSqr(s2, s);
  Load256(Rx, s2);
  ModSub256(Rx, localAx);
  ModSub256(Rx, localBx);

  // Ry = s*(Ax - Rx) - Ay
  ModSub256(dy, localAx, Rx);
  _ModMult(Ry, s, dy);
  ModSub256(Ry, localAy);
}

// Scalar multiplication: result = scalar * G using double-and-add
__device__ void ScalarMultG(uint64_t Rx[4], uint64_t Ry[4], uint64_t scalar[4]) {
  bool isInfinity = true;
  uint64_t curX[4] = { Gx[0][0], Gx[0][1], Gx[0][2], Gx[0][3] };
  uint64_t curY[4] = { Gy[0][0], Gy[0][1], Gy[0][2], Gy[0][3] };

  // Double-and-add from LSB to MSB
  for (int bit = 0; bit < 256; bit++) {
    int wordIdx = bit / 64;
    int bitIdx = bit % 64;

    if ((scalar[wordIdx] >> bitIdx) & 1ULL) {
      if (isInfinity) {
        Load256(Rx, curX);
        Load256(Ry, curY);
        isInfinity = false;
      } else {
        PointAddAffine(Rx, Ry, Rx, Ry, curX, curY);
      }
    }

    if (bit < 255) {
      PointDoubleAffine(curX, curY, curX, curY);
    }
  }

  if (isInfinity) {
    Rx[0] = 0; Rx[1] = 0; Rx[2] = 0; Rx[3] = 0;
    Ry[0] = 0; Ry[1] = 0; Ry[2] = 0; Ry[3] = 0;
  }
}

// Check if Qx matches stego target (uses _stego_value and _stego_mask from constant memory)
__device__ bool CheckTaprootMatch(uint64_t Qx[4]) {
  for (int i = 0; i < 4; i++) {
    if ((Qx[i] & _stego_mask[i]) != (_stego_value[i] & _stego_mask[i])) {
      return false;
    }
  }
  return true;
}

// Taproot compute kernel: Q = P + hash("TapTweak" || P.x) * G
// Simplified taproot kernel - processes just 1 point per thread to avoid timeout
// The scalar multiplication is very slow (256 iterations), so we minimize per-thread work
__device__ void ComputeKeysTaproot(uint64_t *startx, uint64_t *starty,
                                   uint32_t maxFound, uint32_t *out) {

  uint64_t px[4], py[4];

  // Taproot-specific
  uint32_t tweakHash[8];
  uint64_t t_scalar[4];
  uint64_t tGx[4], tGy[4];
  uint64_t Qx[4], Qy[4];

  // Load starting key (this is the point P for this thread)
  __syncthreads();
  Load256A(px, startx);
  Load256A(py, starty);

  // Compute taproot output key: Q = P + hash(P)*G
  // Step 1: t = tagged_hash("TapTweak", P.x)
  SHA256_TapTweak(tweakHash, px);
  HashToScalar256(t_scalar, tweakHash);

  // Step 1.5: Reduce t_scalar mod curve order n (required for correct scalar mult)
  // SHA256 output can be >= n, must reduce before computing t*G
  ModReduceOrder(t_scalar);

  // Step 2: tG = t * G (scalar multiplication)
  ScalarMultG(tGx, tGy, t_scalar);

  // Step 3: Q = P + tG (point addition)
  PointAddAffine(Qx, Qy, px, py, tGx, tGy);

  // Step 4: Check if Q.x matches target prefix
  if (CheckTaprootMatch(Qx)) {
    uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
    uint32_t pos = atomicAdd(out, 1);
    if (pos < maxFound) {
      out[pos*ITEM_SIZE32 + 1] = tid;
      // Bit 15 = mode (taproot=1), bits 0-14 = iteration counter
      out[pos*ITEM_SIZE32 + 2] = (uint32_t)((_taproot_iter << 16) | (1 << 15));
      // Store P.x MSB (the internal key we're tweaking)
      out[pos*ITEM_SIZE32 + 3] = (uint32_t)(px[3] >> 32);
      out[pos*ITEM_SIZE32 + 4] = (uint32_t)(px[3]);
      // Remaining slots available for future use
    }
  }

  // Update starting point: P = P + G (simple increment for next batch)
  // This is much faster than full scalar mult - just one point addition
  // Formula: R = P + G
  //   s = (G.y - P.y) / (G.x - P.x)
  //   R.x = s^2 - P.x - G.x
  //   R.y = s * (P.x - R.x) - P.y
  uint64_t dy[4], _s[4], _p2[4];
  uint64_t oldPx[4], oldPy[4];  // Save original P before modification
  Load256(oldPx, px);
  Load256(oldPy, py);

  ModSub256(dy, Gy[0], py);     // dy = G.y - P.y
  uint64_t dx[5];  // _ModInv requires 5-element array (320 bits)
  ModSub256(dx, Gx[0], px);     // dx = G.x - P.x
  dx[4] = 0;  // Clear 5th element for _ModInv

  // Inline modular inverse for single point
  uint64_t inv[5];  // _ModInv requires 5-element array (320 bits)
  Load256(inv, dx);
  inv[4] = 0;  // Clear 5th element for _ModInv
  _ModInv(inv);

  _ModMult(_s, dy, inv);        // s = (G.y - P.y) / (G.x - P.x)
  _ModSqr(_p2, _s);             // _p2 = s^2

  ModSub256(px, _p2, oldPx);    // px = s^2 - P.x (use saved oldPx)
  ModSub256(px, Gx[0]);         // px = s^2 - P.x - G.x = R.x

  ModSub256(py, oldPx, px);     // py = P.x - R.x (use saved oldPx, not Gx!)
  _ModMult(py, _s);             // py = s * (P.x - R.x)
  ModSub256(py, oldPy);         // py = s * (P.x - R.x) - P.y = R.y

  // Store updated point for next kernel call
  __syncthreads();
  Store256A(startx, px);
  Store256A(starty, py);

}
