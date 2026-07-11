import io
import json
import tempfile
import unittest
from pathlib import Path

from daily_brief.synology import _snmp_values, fetch_synology_status


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class SynologyTests(unittest.TestCase):
    def test_parses_snmp_table_values(self) -> None:
        output = "\n".join(
            [
                "HOST-RESOURCES-MIB::hrStorageDescr.57 = STRING: /volume1",
                "HOST-RESOURCES-MIB::hrStorageDescr.58 = STRING: /volume2",
            ]
        )
        self.assertEqual(_snmp_values(output), {57: "/volume1", 58: "/volume2"})

    def test_reports_storage_and_healthy_status(self) -> None:
        def opener(url, timeout):
            parameters = url.data.decode()
            if "method=login" in parameters:
                payload = {"success": True, "data": {"sid": "sid"}}
            elif "load_info" in parameters:
                payload = {
                    "success": True,
                    "data": {
                        "volumes": [
                            {"status": "normal", "size": {"total": 1000, "used": 420}}
                        ]
                    },
                }
            else:
                payload = {"success": True, "data": {}}
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "synology.json"
            config.write_text(
                json.dumps(
                    {
                        "url": "https://nas.test:5001",
                        "username": "dailybrief",
                        "password": "secret",
                    }
                ),
                encoding="utf-8",
            )
            config.chmod(0o600)
            result = fetch_synology_status(opener, root / "cache", config)

        self.assertTrue(result.reachable)
        self.assertEqual(result.storage_percent, 42)
        self.assertEqual(result.warnings, [])

    def test_reports_security_scan_issues(self) -> None:
        def opener(url, timeout):
            parameters = url.data.decode()
            if "method=login" in parameters:
                data = {"sid": "sid"}
            elif "SYNO.Core.SecurityScan.Status" in parameters:
                data = {"issue_count": 2}
            elif "load_info" in parameters:
                data = {"volumes": []}
            else:
                data = {}
            return Response(json.dumps({"success": True, "data": data}).encode())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "synology.json"
            config.write_text(
                json.dumps(
                    {
                        "url": "https://nas.test:5001",
                        "username": "dailybrief",
                        "password": "secret",
                    }
                ),
                encoding="utf-8",
            )
            config.chmod(0o600)
            result = fetch_synology_status(opener, root / "cache", config)

        self.assertEqual(result.warnings, ["2 securitywaarschuwing(en)"])
