#!/bin/bash
# Complete repository rebuild to remove all large objects

set -e

echo "=== Complete Git Repository Rebuild ==="
echo ""
echo "This will:"
echo "1. Create a new orphan branch with current code"
echo "2. Commit all current files"
echo "3. Force push to replace main"
echo "4. Delete old branches"
echo ""

# Save current state
CURRENT_DIR=$(pwd)
TEMP_DIR=$(mktemp -d)

echo "Step 1: Backing up current code to $TEMP_DIR"
cp -r . "$TEMP_DIR/backup"

echo "Step 2: Creating new orphan branch"
git checkout --orphan new-main

echo "Step 3: Staging all current files"
git add -A

echo "Step 4: Committing with clean history"
git commit -m "Clean repository rebuild - remove large objects from history"

echo "Step 5: Force pushing to main"
git push origin new-main:main --force

echo "Step 6: Cleaning up"
git branch -D main
git checkout main

echo ""
echo "=== Repository Rebuild Complete ==="
echo "Repository is now clean with no large objects in history"
