import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('local_demo_under_test', Path(__file__).resolve().parents[1] / 'scripts/run_local_demo.py')
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)


class LocalDemoTests(unittest.TestCase):
    def test_distinct_unprivileged_ports(self):
        local.validate_ports([5173, 8000, 8001])

    def test_conflicting_ports_rejected(self):
        with self.assertRaises(ValueError):
            local.validate_ports([5173, 5173, 8001])

    def test_privileged_or_invalid_ports_rejected(self):
        for port in (80, 0, 65536):
            with self.subTest(port=port), self.assertRaises(ValueError):
                local.validate_ports([5173, port, 8001])

    def test_cleanup_signals_owned_group_even_if_leader_has_exited(self):
        process = Mock(pid=12345)
        process.poll.return_value = 0
        with patch.object(local.os, 'name', 'posix'), patch.object(local.os, 'killpg') as kill_group:
            local.stop_process(process)
        kill_group.assert_called_once_with(12345, local.signal.SIGTERM)
        process.wait.assert_called_once_with(timeout=5)
