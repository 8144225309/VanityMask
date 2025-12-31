#!/usr/bin/env python
"""Fix Vanity.cpp to add sigMode initialization."""

with open('Vanity.cpp', 'r') as f:
    content = f.read()

# The old text we want to replace
old_text = '''  } else if (txidMode) {
    nbPrefix = 0;
    onlyFull = false;
    searchType = P2PKH;  // Doesn't matter for txid mode, but needs to be set
    _difficulty = pow(2.0, stegoTarget.numBits);
    printf("TXID mode: Matching %d bits of transaction ID\\n", stegoTarget.numBits);
  } else if (!hasPattern) {'''

# The new text with sigMode added before txidMode
new_text = '''  } else if (sigMode) {
    nbPrefix = 0;
    onlyFull = false;
    searchType = P2PKH;  // Doesn't matter for sig mode, but needs to be set
    _difficulty = pow(2.0, stegoTarget.numBits);
    printf("Signature mode: Matching %d bits of R.x coordinate\\n", stegoTarget.numBits);
  } else if (txidMode) {
    nbPrefix = 0;
    onlyFull = false;
    searchType = P2PKH;  // Doesn't matter for txid mode, but needs to be set
    _difficulty = pow(2.0, stegoTarget.numBits);
    printf("TXID mode: Matching %d bits of transaction ID\\n", stegoTarget.numBits);
  } else if (!hasPattern) {'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('Vanity.cpp', 'w') as f:
        f.write(content)
    print("Successfully added sigMode initialization!")
else:
    print("ERROR: Could not find the target text to replace")
    print("Looking for patterns...")
    if "} else if (txidMode) {" in content:
        print("  Found: '} else if (txidMode) {'")
    if "nbPrefix = 0;" in content:
        print("  Found: 'nbPrefix = 0;'")
