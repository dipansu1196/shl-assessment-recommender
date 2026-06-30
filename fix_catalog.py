import json
import re

print("Fixing catalog.json encoding issues...")

# Read file with error handling
with open('data/catalog_fresh.json', 'rb') as f:
    raw_bytes = f.read()

print(f"Read {len(raw_bytes)} bytes")

# Try UTF-8 with error replacement
text = raw_bytes.decode('utf-8', errors='replace')

# Remove control characters except newlines/tabs
text_clean = ''.join(char if ord(char) >= 32 or char in '\n\r\t' else ' ' for char in text)

print("Removed control characters")

# Try parsing
try:
    catalog = json.loads(text_clean)
    print(f"SUCCESS: Loaded {len(catalog)} assessments from catalog")
    
    # Save cleaned version
    with open('data/catalog.json', 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Saved cleaned catalog to data/catalog.json")
    
    # Show sample
    print(f"\nSample assessment:")
    print(f"  Name: {catalog[0]['name']}")
    print(f"  URL: {catalog[0]['link']}")
    
except json.JSONDecodeError as e:
    print(f"JSON Error at position {e.pos}: {e.msg}")
    # Show context around error
    start = max(0, e.pos - 100)
    end = min(len(text_clean), e.pos + 100)
    print(f"Context: ...{text_clean[start:end]}...")
