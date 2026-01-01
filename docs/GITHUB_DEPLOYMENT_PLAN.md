# GitHub Deployment Plan

## Repository Information

- **Remote**: https://github.com/8144225309/VanityMask
- **Current Branch**: master
- **Commits Ahead of Origin**: 4

## Commits to Push

```
a8d35e5 Fix taproot GPU mode - correct SetKeys and SHA256_TapTweak  <-- LATEST (main fix)
38eb9e4 Fix SHA256_TapTweak byte order - add bswap32 for correct hash
74553c6 WIP: Taproot debugging - key reconstruction analysis
0539993 Add comprehensive test suite with GPU monitoring and crypto verification
```

## Pre-Push Checklist

- [x] Code compiles without errors
- [x] Taproot mode tested and verified working
- [x] Python verification scripts confirm correct output
- [x] Debug output removed from production code
- [x] Documentation added (docs/TAPROOT_GPU_FIX.md)
- [x] Test scripts added (tests/*.py)

## Deployment Options

### Option 1: Push All Commits (Recommended)

Push all 4 commits preserving full development history:

```bash
git push origin master
```

**Pros**: Full history preserved, shows debugging process
**Cons**: Includes WIP commits

### Option 2: Squash and Push

Squash all 4 commits into a single clean commit:

```bash
# Create new branch from origin/master
git checkout -b taproot-fix origin/master

# Cherry-pick with squash
git merge --squash master

# Commit with clean message
git commit -m "Add working taproot GPU mode with BIP-340/341 support

Features:
- Taproot post-tweak key grinding (Q = P + TapTweak(P.x)*G)
- GPU-accelerated tagged hash and point arithmetic
- Python verification test suite
- Comprehensive documentation

Fixes SetKeys() kernel corruption and SHA256_TapTweak byte order."

# Push and set upstream
git push -u origin taproot-fix

# Create PR or merge to master
```

**Pros**: Clean single commit
**Cons**: Loses detailed development history

### Option 3: Interactive Rebase (Advanced)

Rebase to clean up WIP commits while keeping meaningful ones:

```bash
git rebase -i origin/master
# Mark 74553c6 as "fixup" to squash into previous
# Keep other commits
git push origin master
```

## Recommended Approach

**Option 1 (Push All)** is recommended because:
1. The commits tell a logical story of the fix
2. No destructive history rewriting
3. Simple single command
4. Preserves debugging context for future reference

## Push Command

```bash
cd C:\pirqjobs\vanitymask-workshop\VanityMask
git push origin master
```

## Post-Push Verification

After pushing, verify on GitHub:
1. Check commits appear correctly
2. Verify docs/TAPROOT_GPU_FIX.md is readable
3. Confirm tests/ directory is present
4. Optional: Create a release tag

```bash
git tag -a v1.20-taproot -m "Add taproot GPU grinding mode"
git push origin v1.20-taproot
```

## Rollback Plan

If issues are discovered after push:

```bash
# Revert to backup branch
git checkout backup/pre-taproot-gpu

# Or revert specific commit
git revert a8d35e5

# Force push only if absolutely necessary (dangerous!)
# git push --force origin master
```

## Release Notes Template

```markdown
## VanityMask v1.20 - Taproot Support

### New Features
- **Taproot GPU Mode**: Grind for taproot addresses where the tweaked
  output key Q.x matches a target prefix
- BIP-340/341 compliant tagged hash implementation
- Python verification test suite

### Usage
\`\`\`bash
# Find taproot address with Q.x starting with 0000
VanitySearch.exe -taproot -tx 0000 --prefix 2 -gpu -stop
\`\`\`

### Technical Details
- GPU computes: Q = P + SHA256("TapTweak", P.x) * G
- Matches Q.x against target prefix
- ~50-100x slower than mask mode due to scalar multiplication

### Bug Fixes
- Fixed SetKeys() kernel corruption affecting taproot/stego modes
- Fixed SHA256_TapTweak byte order for correct hash computation
```
