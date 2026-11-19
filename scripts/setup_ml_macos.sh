#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert sys.version_info[:2] == (3, 12), "Use Python 3.12 for this pinned runtime"'
if [ ! -x .venv-ml/bin/python ]; then
  python3 -m venv --system-site-packages .venv-ml
fi
.venv-ml/bin/python -m pip install --cache-dir data/local/pip-cache -r requirements-ml-macos.txt
PYTHONPATH=src .venv-ml/bin/python -m unittest discover -s tests -p 'test_training_*.py' -v
