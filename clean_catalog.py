import json
import re

# Read the file as binary
with open('data/catalog.json', 'rb') as f:
    raw_data = f.read()

# Decode with replacement
text = raw_data.decode('utf-8', errors='replace')

# Remove control characters except whitespace
text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)

# Try to parse
try:
    data = json.loads(text)
    print(f"Successfully parsed {len(data)} records")
except json.JSONDecodeError as e:
    print(f"Parse error: {e}")
    # Fallback: try ijson if available
    try:
        import ijson
        data = []
        with open('data/catalog.json', 'rb') as f:
            for record in ijson.items(f, 'item'):
                data.append(record)
        print(f"ijson parsed {len(data)} records")
    except:
        print("ijson not available. Install with: pip install ijson")
        data = []

# Save cleaned version
if data:
    with open('data/catalog_clean.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} records to catalog_clean.json")
else:
    print("No data to save")
