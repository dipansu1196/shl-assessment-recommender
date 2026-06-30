import json
import re

print("Repairing catalog JSON with embedded newlines...")

with open('data/catalog_fresh.json', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

# Fix embedded newlines in JSON strings: "key": "value\nwith\nnewline"
# Replace newlines inside quoted strings with space
def fix_json_newlines(text):
    # Find all strings and replace newlines with space
    result = []
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text):
        if escape_next:
            result.append(char)
            escape_next = False
            continue
            
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            result.append(char)
            continue
        
        if in_string and char in '\r\n':
            result.append(' ')  # Replace newline with space
        else:
            result.append(char)
    
    return ''.join(result)

text = fix_json_newlines(text)

try:
    data = json.loads(text)
    print(f"SUCCESS: Loaded {len(data)} assessments")
    
    with open('data/catalog.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Saved cleaned catalog to data/catalog.json")
    print(f"\nSample: {data[0]['name']}")
    
except Exception as e:
    print(f"Error: {e}")
