"""Run only the experimental interpreter service on loopback."""
import argparse
import os
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8002)
    parser.add_argument('--web-port', type=int, default=5173)
    args = parser.parse_args()
    if any(not 1024 <= port <= 65535 for port in (args.port, args.web_port)) or args.port == args.web_port:
        parser.error('Use distinct unprivileged loopback ports')
    python = root / '.venv-ml/bin/python'
    if not python.is_file():
        parser.error('Install the Mac ML environment using scripts/setup_ml_macos.sh first')
    # Reuse the existing pinned API dependencies without changing either env.
    # A fresh combined environment can instead install requirements-interpreter.txt.
    app_packages = root / '.venv/lib/python3.12/site-packages'
    paths = [str(root / 'src')]
    if app_packages.is_dir():
        paths.append(str(app_packages))
    environment = os.environ | {'PYTHONPATH': os.pathsep.join(paths), 'NEOSIGNIS_WEB_PORT': str(args.web_port),
                                'HF_HOME': str(root / 'data/local/models/unisign/hf-cache')}
    os.chdir(root)
    os.execve(str(python), [str(python), '-m', 'uvicorn', 'neosignis.experiment:app', '--host', '127.0.0.1',
                            '--port', str(args.port), '--no-access-log'], environment)


if __name__ == '__main__':
    main()
