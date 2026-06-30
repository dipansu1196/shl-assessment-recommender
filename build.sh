#!/bin/bash
set -e

# Create pip config for CPU-only PyTorch
mkdir -p $HOME/.config/pip
cat > $HOME/.config/pip/pip.conf << 'EOF'
[global]
index-url = https://download.pytorch.org/whl/cpu
extra-index-url = https://pypi.org/simple/
EOF

# Install dependencies
pip install -r requirements.txt
