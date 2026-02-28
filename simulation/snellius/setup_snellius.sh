#!/bin/bash
# One-time setup for Snellius
# Run from local machine: ssh snellius "bash -s" < snellius/setup_snellius.sh

set -e

echo "=== Setting up Origins on Snellius ==="

# Create directory structure
mkdir -p ~/origins/simulation/logs
mkdir -p ~/origins/simulation/data/runs
mkdir -p ~/origins/simulation/data/experiment_log

# Create Python venv
echo "Creating Python venv..."
python3 -m venv ~/origins/venv
~/origins/venv/bin/pip install --upgrade pip
~/origins/venv/bin/pip install openai pyyaml numpy python-dotenv scipy pandas

# Verify
echo ""
echo "=== Verification ==="
~/origins/venv/bin/python -c "import openai; print(f'openai: {openai.__version__}')"
~/origins/venv/bin/python -c "import yaml; print('pyyaml: ok')"
~/origins/venv/bin/python -c "import numpy; print(f'numpy: {numpy.__version__}')"
~/origins/venv/bin/python -c "import scipy; print(f'scipy: {scipy.__version__}')"
~/origins/venv/bin/python -c "import pandas; print(f'pandas: {pandas.__version__}')"

echo ""
echo "=== Setup complete ==="
echo "Next: rsync simulation code, then submit jobs"
