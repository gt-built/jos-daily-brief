import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import SynologyStatus


CONFIG_PATH = Path.home() / ".config" / "jos-daily-brief" / "synology.json"
SNMP_CONFIG_PATH = Path.home() / ".config" / "jos-daily-brief" / "synology-snmp.json"

STORAGE_OIDS = {
    "description": ".1.3.6.1.2.1.25.2.3.1.3",
    "allocation_unit": ".1.3.6.1.2.1.25.2.3.1.4",
    "size": ".1.3.6.1.2.1.25.2.3.1.5",
    "used": ".1.3.6.1.2.1.25.2.3.1.6",
}


def _credentials(path: Path = CONFIG_PATH) -> Dict[str, str]:
    if path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            raise PermissionError(f"{path} moet bestandsrechten 0600 hebben")
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "url": os.environ["SYNOLOGY_URL"],
        "username": os.environ["SYNOLOGY_USERNAME"],
        "password": os.environ["SYNOLOGY_PASSWORD"],
    }


def _request(opener: Callable, base_url: str, path: str, params: Dict) -> Dict:
    request = Request(
        f"{base_url.rstrip('/')}/webapi/{path}",
        data=urlencode(params).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with opener(request, timeout=10) as response:
        payload = json.load(response)
    if not payload.get("success"):
        raise OSError(f"Synology API-fout: {payload.get('error', {}).get('code', 'onbekend')}")
    return payload.get("data", {})


def _storage(volumes: List[Dict]) -> Optional[int]:
    totals = 0
    used = 0
    for volume in volumes:
        size = volume.get("size", volume)
        try:
            total = int(size.get("total", size.get("size_total", 0)))
            occupied = int(size.get("used", size.get("size_used", 0)))
        except (TypeError, ValueError):
            continue
        totals += total
        used += occupied
    if totals <= 0:
        return None
    return round((used / totals) * 100)


def _snmp_values(output: str) -> Dict[int, str]:
    values = {}
    for line in output.splitlines():
        match = re.search(r"\.(\d+)\s+=\s+\S+:\s+(.*)$", line)
        if match:
            values[int(match.group(1))] = match.group(2).strip()
    return values


def _snmp_status(
    config_path: Path,
    cache_dir: Path,
    now: Optional[datetime],
) -> SynologyStatus:
    mode = stat.S_IMODE(config_path.stat().st_mode)
    if mode & 0o077:
        raise PermissionError(f"{config_path} moet bestandsrechten 0600 hebben")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    def load() -> Dict:
        executable = shutil.which("snmpwalk")
        if not executable:
            raise OSError("snmpwalk is niet geïnstalleerd")
        with tempfile.TemporaryDirectory(prefix="dailybrief-snmp-") as directory:
            snmp_config = Path(directory) / "snmp.conf"
            snmp_config.write_text(
                "\n".join(
                    [
                        f"defSecurityName {config['username']}",
                        "defSecurityLevel authPriv",
                        f"defAuthType {config['auth_protocol']}",
                        f"defAuthPassphrase {config['auth_password']}",
                        f"defPrivType {config['privacy_protocol']}",
                        f"defPrivPassphrase {config['privacy_password']}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            snmp_config.chmod(0o600)
            environment = {**os.environ, "SNMPCONFPATH": directory}
            tables = {}
            for name, oid in STORAGE_OIDS.items():
                result = subprocess.run(
                    [
                        executable,
                        "-v",
                        "3",
                        f"{config['host']}:{config.get('port', 161)}",
                        oid,
                    ],
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=15,
                )
                if result.returncode:
                    raise OSError(result.stderr.strip() or "SNMP-opvraag mislukt")
                tables[name] = _snmp_values(result.stdout)

        volumes = []
        descriptions = tables["description"]
        for index, description in descriptions.items():
            if not description.startswith("/volume"):
                continue
            try:
                unit = int(tables["allocation_unit"][index].split()[0])
                total = int(tables["size"][index].split()[0]) * unit
                used = int(tables["used"][index].split()[0]) * unit
            except (KeyError, ValueError):
                continue
            volumes.append(
                {
                    "name": description.lstrip("/"),
                    "total": total,
                    "used": used,
                }
            )
        if not volumes:
            raise OSError("Geen Synology-volumes gevonden via SNMP")
        total = sum(volume["total"] for volume in volumes)
        used = sum(volume["used"] for volume in volumes)
        warnings = [
            f"{volume['name']} {round(volume['used'] / volume['total'] * 100)}% gebruikt"
            for volume in volumes
            if volume["total"] and volume["used"] / volume["total"] >= 0.85
        ]
        return {
            "reachable": True,
            "storage_percent": round(used / total * 100),
            "warnings": warnings,
        }

    cached = load_with_cache(
        "synology-snmp",
        load,
        fresh_for=timedelta(minutes=5),
        stale_for=timedelta(hours=1),
        cache_dir=cache_dir,
        now=now,
    )
    return SynologyStatus(
        reachable=True,
        storage_percent=cached.payload["storage_percent"],
        warnings=cached.payload.get("warnings", []),
        stale=cached.stale,
    )


def fetch_synology_status(
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    config_path: Path = CONFIG_PATH,
    now: Optional[datetime] = None,
) -> SynologyStatus:
    if config_path == CONFIG_PATH and SNMP_CONFIG_PATH.exists():
        return _snmp_status(SNMP_CONFIG_PATH, cache_dir, now)

    def load() -> Dict:
        config = _credentials(config_path)
        base_url = config["url"]
        api_info = _request(
            opener,
            base_url,
            "query.cgi",
            {
                "api": "SYNO.API.Info",
                "version": "1",
                "method": "query",
                "query": (
                    "SYNO.API.Auth,SYNO.Core.System,SYNO.Storage.CGI.Storage,"
                    "SYNO.Core.SecurityScan.Status"
                ),
            },
        )

        def call(api: str, method: str, fallback_path: str, fallback_version: int, **params):
            info = api_info.get(api, {})
            return _request(
                opener,
                base_url,
                info.get("path", fallback_path),
                {
                    "api": api,
                    "version": min(fallback_version, int(info.get("maxVersion", fallback_version))),
                    "method": method,
                    **params,
                },
            )

        auth = call(
            "SYNO.API.Auth",
            "login",
            "auth.cgi",
            7,
            account=config["username"],
            passwd=config["password"],
            format="sid",
            enable_syno_token="yes",
        )
        sid = auth["sid"]
        syno_token = auth.get("synotoken")
        authentication = {
            "_sid": sid,
            **({"SynoToken": syno_token} if syno_token else {}),
        }
        system = call(
            "SYNO.Core.System",
            "info",
            "entry.cgi",
            3,
            **authentication,
        )
        storage = call(
            "SYNO.Storage.CGI.Storage",
            "load_info",
            "entry.cgi",
            1,
            **authentication,
        )
        security = call(
            "SYNO.Core.SecurityScan.Status",
            "get",
            "entry.cgi",
            1,
            **authentication,
        )
        warnings = []
        if system.get("systemp_warning"):
            warnings.append("temperatuurwaarschuwing")
        volumes = storage.get("volumes", [])
        for volume in volumes:
            status = str(volume.get("status", "normal")).lower()
            if status not in ("normal", "healthy", "1"):
                warnings.append("opslagwaarschuwing")
                break
        issue_count = 0
        for key, value in security.items():
            if key.lower() in (
                "risk_count",
                "warning_count",
                "danger_count",
                "issue_count",
                "security_issue_count",
            ):
                try:
                    issue_count += int(value)
                except (TypeError, ValueError):
                    continue
        if issue_count:
            warnings.append(f"{issue_count} securitywaarschuwing(en)")
        return {
            "reachable": True,
            "storage_percent": _storage(volumes),
            "warnings": warnings,
        }

    cached = load_with_cache(
        "synology",
        load,
        fresh_for=timedelta(minutes=5),
        stale_for=timedelta(hours=1),
        cache_dir=cache_dir,
        now=now,
    )
    return SynologyStatus(
        reachable=cached.payload.get("reachable", True),
        storage_percent=cached.payload.get("storage_percent"),
        warnings=cached.payload.get("warnings", []),
        stale=cached.stale,
    )
