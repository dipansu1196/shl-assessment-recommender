import json
import re

print("Aggressive catalog fix...")

with open('data/catalog_fresh.json', 'rb') as f:
    raw = f.read()

text = raw.decode('utf-8', errors='replace')

# Remove ALL control characters including newlines inside strings
text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', text)

# Also handle \r and unusual whitespace
text = text.replace('\r', ' ')

try:
    data = json.loads(text)
    print(f"SUCCESS: Loaded {len(data)} items")
    
    with open('data/catalog.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print("Saved to data/catalog.json")
    print(f"First item: {data[0]['name']}")
    
except json.JSONDecodeError as e:
    print(f"Failed: {e}")
    print(f"Position: {e.pos}")
    # Try finding and showing the bad character
    if e.pos < len(text):
        char_code = ord(text[e.pos])
        print(f"Bad character code: {char_code} at position {e.pos}")
        start = max(0, e.pos - 50)
        end = min(len(text), e.pos + 50)
        print(f"Context: {repr(text[start:end])}")
