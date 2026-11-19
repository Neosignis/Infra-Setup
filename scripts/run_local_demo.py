"""Run the loopback-only camera workbench, API and worker without Docker/AWS."""
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = ROOT / 'apps' / 'workbench'


def validate_ports(ports):
    if len(set(ports)) != len(ports):
        raise ValueError('Web, API and worker ports must be different')
    if any(type(port) is not int or not 1024 <= port <= 65535 for port in ports):
        raise ValueError('Use local ports between 1024 and 65535')


def check_ports(ports):
    validate_ports(ports)
    # Bind all at once so a duplicate/occupied port fails before starting children.
    with ExitStack() as stack:
        for port in ports:
            connection = stack.enter_context(socket.socket())
            try:
                connection.bind(('127.0.0.1', port))
            except OSError:
                raise RuntimeError(f'Local port {port} is in use; stop the old process or choose another port') from None


def stop_process(process):
    # A terminated npm/shell leader can leave descendants in its owned group.
    if os.name != 'posix' and process.poll() is not None:
        return
    try:
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=5)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=5)


def wait_for_http(url, processes, timeout=30):
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError('A local service stopped during startup; see its terminal output above')
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, OSError, TimeoutError):
            pass
        time.sleep(.15)
    raise RuntimeError('A local service did not start in time; see terminal output above')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web-port', type=int, default=5173)
    parser.add_argument('--api-port', type=int, default=8000)
    parser.add_argument('--worker-port', type=int, default=8001)
    parser.add_argument('--with-interpreter', action='store_true', help='Start the experimental local video model service')
    parser.add_argument('--interpreter-port', type=int, default=8002)
    parser.add_argument('--open', action='store_true', help='Open the workbench in the default browser')
    args = parser.parse_args()
    processes = []
    # Test runners and terminal shutdown use SIGTERM; still clean up child process groups.
    if os.name == 'posix':
        def terminate(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, terminate)
    try:
        check_ports([args.web_port, args.api_port, args.worker_port] + ([args.interpreter_port] if args.with_interpreter else []))
        node, npm = shutil.which('node'), shutil.which('npm')
        if not node or not npm:
            raise RuntimeError('Install Node.js 24, then run npm ci inside apps/workbench')
        version = subprocess.check_output([node, '--version'], text=True).strip()
        if int(version.lstrip('v').split('.')[0]) != 24:
            raise RuntimeError('This workbench is tested with Node.js 24; select Node 24 before running')
        if not (WORKBENCH / 'node_modules' / 'vite').exists():
            raise RuntimeError('Frontend dependencies are missing. Run: npm --prefix apps/workbench ci')
        venv_python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        python = str(venv_python) if venv_python.exists() else sys.executable
        checked = subprocess.run([python, '-c', 'import sys, fastapi, uvicorn, jwt; assert sys.version_info[:2] == (3, 12)'], capture_output=True)
        if checked.returncode:
            raise RuntimeError('Use Python 3.12 and install requirements.txt in .venv before running the demo')
        environment = os.environ | {
            'APP_ENV': 'local', 'AUTH_MODE': 'dev_token',
            'DEV_API_TOKEN': secrets.token_urlsafe(32),
            'INFERENCE_URL': f'http://127.0.0.1:{args.worker_port}',
            'NEOSIGNIS_API_PORT': str(args.api_port), 'NEOSIGNIS_WEB_PORT': str(args.web_port),
            'NEOSIGNIS_EXPERIMENT_PORT': str(args.interpreter_port),
            'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1',
            # A camera demo never enables an ambient/unreviewed provider by accident.
            'ENGINE_PROVIDER': '',
        }
        for module, port in [('worker', args.worker_port), ('api', args.api_port)]:
            processes.append(subprocess.Popen(
                [python, '-m', 'uvicorn', f'neosignis.{module}:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'],
                cwd=ROOT, env=environment, start_new_session=os.name == 'posix',
            ))
            wait_for_http(f'http://127.0.0.1:{port}/healthz', processes)
        if args.with_interpreter:
            processes.append(subprocess.Popen([sys.executable, str(ROOT / 'scripts/run_interpreter.py'), '--port', str(args.interpreter_port), '--web-port', str(args.web_port)], cwd=ROOT, env=environment, start_new_session=os.name == 'posix'))
            wait_for_http(f'http://127.0.0.1:{args.interpreter_port}/healthz', processes)
        processes.append(subprocess.Popen([npm, 'run', 'dev'], cwd=WORKBENCH, env=environment, start_new_session=os.name == 'posix'))
        url = f'http://127.0.0.1:{args.web_port}'
        wait_for_http(url, processes)
        print(f'\nNeosignis camera workbench: {url}', flush=True)
        print(('Experimental buffered ASL suggestions enabled; quality and real-time gates have not passed.' if args.with_interpreter else 'Interpreter UI and Contributor Studio available. Add --with-interpreter to start the experimental model.') + '\nSigned playback is not installed. Press Ctrl+C to stop these local services.\n', flush=True)
        if args.open:
            webbrowser.open(url)
        while all(process.poll() is None for process in processes):
            time.sleep(.3)
        raise RuntimeError('A local service stopped; see its terminal output above')
    except KeyboardInterrupt:
        print('\nStopping the local workbench.', flush=True)
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'Local demo: {exc}', file=sys.stderr)
        return 1
    finally:
        for process in reversed(processes):
            stop_process(process)


if __name__ == '__main__':
    raise SystemExit(main())
