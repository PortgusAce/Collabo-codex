"""Local-only setup/lifecycle CLI. No plaintext key command-line arguments."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import zipfile
import asyncio

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from configuration import RUNTIME, FILES_CONFIG, read_json, write_json, validate_file_config

TUNNEL_CONFIG = RUNTIME / "tunnel.json"
KEY_FILE = RUNTIME / "runtime-key.dpapi"
KEY_ENV = "COLLABO_TUNNEL_KEY"


def native_env():
    return {**os.environ, "XDG_STATE_HOME": str(RUNTIME / "state"),
            "XDG_CONFIG_HOME": str(RUNTIME / "config")}


def install_tunnel(proxy=None):
    import requests
    if sys.platform != "win32":
        raise ValueError("The setup helper currently supports Windows only; file MCP supports other Python hosts")
    arch = {"amd64": "amd64", "x86_64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower())
    if not arch:
        raise ValueError("Unsupported Windows architecture")
    session = requests.Session()
    session.headers["User-Agent"] = "Collabo-codex-installer"
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
    release = session.get("https://github.com/openai/tunnel-client/releases/latest", timeout=45)
    release.raise_for_status()
    version = release.url.rsplit("/", 1)[-1]
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-.][\w.]+)?", version):
        raise ValueError("Cannot resolve the official tunnel-client release")
    asset = f"tunnel-client-{version}-windows-{arch}.zip"
    release_base = f"https://github.com/openai/tunnel-client/releases/download/{version}"
    checks = session.get(release_base + "/SHA256SUMS.txt", timeout=45)
    checks.raise_for_status()
    expected = next((line.split()[0] for line in checks.text.splitlines()
                     if len(line.split()) >= 2 and line.split()[-1].lstrip("*") == asset), None)
    if not expected or not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
        raise ValueError("Official checksum is missing; archive will not be installed")
    destination = BASE / "bin" / version
    executable = destination / "tunnel-client.exe"
    if executable.exists():
        manifest = read_json(RUNTIME / "tunnel-install.json", {})
        if manifest.get("archive_sha256") == expected and manifest.get("executable_sha256") == hashlib.sha256(executable.read_bytes()).hexdigest():
            return str(executable)
    archive = RUNTIME / "downloads" / asset
    archive.parent.mkdir(parents=True, exist_ok=True)
    digest, size = hashlib.sha256(), 0
    with session.get(release_base + "/" + asset, stream=True, timeout=(30, 90)) as response:
        response.raise_for_status()
        with archive.open("wb") as stream:
            for chunk in response.iter_content(1024 * 1024):
                size += len(chunk)
                if size > 150 * 1024 * 1024:
                    raise ValueError("Archive exceeds the 150 MB download limit")
                digest.update(chunk)
                stream.write(chunk)
    if digest.hexdigest() != expected.lower():
        raise ValueError("Official archive SHA256 mismatch; no executable was installed")
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Archive contains an unsafe extraction path")
        bundle.extractall(destination)
    if not executable.is_file():
        raise ValueError("Official archive contains no tunnel-client.exe")
    write_json(RUNTIME / "tunnel-install.json", {"version": version, "path": str(executable),
               "archive_sha256": expected.lower(), "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()})
    return str(executable)


def client_path():
    metadata = read_json(RUNTIME / "tunnel-install.json", {})
    path = Path(metadata.get("path", ""))
    if not path.is_file():
        raise ValueError("Install the official tunnel client using the setup tool first")
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata.get("executable_sha256"):
        raise ValueError("Tunnel executable changed; reinstall it with the setup tool")
    return str(path)


def runtime_key():
    if sys.platform != "win32":
        raise ValueError("Windows DPAPI credentials can only be opened by their Windows user")
    import win32crypt
    encrypted = base64.b64decode(KEY_FILE.read_text().strip(), validate=True)
    return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode("utf-8")


def run_client(args, *, env=None, key=None):
    result = subprocess.run([client_path(), *args], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", env=env or native_env(), timeout=120,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    output = result.stdout + result.stderr
    if key:
        output = output.replace(key, "[REDACTED]")
    if result.returncode:
        write_json(RUNTIME / "last-error.json", {"command": args[0], "diagnostic": output})
        raise ValueError("Tunnel command failed; see .runtime/last-error.json")
    return json.loads(result.stdout.replace(key, "[REDACTED]") if key else result.stdout)


def connect_tunnel():
    settings = read_json(TUNNEL_CONFIG, {})
    tunnel_id = settings.get("tunnel_id", "")
    if not re.fullmatch(r"tunnel_(?:[a-z0-9]{4}_)?[a-z0-9]{32}", tunnel_id):
        raise ValueError("Configure a valid Tunnel ID in the local setup tool")
    env, key = native_env(), runtime_key()
    env[KEY_ENV] = key
    proxy = settings.get("proxy")
    if proxy:
        import socket
        from urllib.parse import urlsplit
        parsed = urlsplit(proxy)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or not parsed.port:
            raise ValueError("Proxy must be an HTTP(S) URL including a port")
        with socket.create_connection((parsed.hostname, parsed.port), timeout=3):
            pass
        env.update({"HTTPS_PROXY": proxy, "HTTP_PROXY": proxy, "NO_PROXY": "localhost,127.0.0.1,::1"})
    profiles = RUNTIME / "profiles"
    command = subprocess.list2cmdline([Path(sys.executable).as_posix(), (BASE / "gateway.py").as_posix()])
    # Generate/refresh the native profile; only an environment reference is persisted.
    init = subprocess.run([client_path(), "init", "--force", "--profile", "collabo-codex", "--profile-dir", str(profiles),
                          "--tunnel-id", tunnel_id, "--mcp-command", command,
                          "--control-plane-api-key-ref", "env:" + KEY_ENV,
                          "--health-listen-addr", "127.0.0.1:0"], env=env, capture_output=True, timeout=30,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if init.returncode:
        raise ValueError("Could not generate the native tunnel profile")
    doctor = run_client(["doctor", "--profile", "collabo-codex", "--profile-dir", str(profiles), "--json"], env=env, key=key)
    write_json(RUNTIME / "doctor.json", doctor)
    run_client(["runtimes", "connect", "--alias", "collabo-codex", "--profile", "collabo-codex", "--profile-dir", str(profiles),
                "--tunnel-id", tunnel_id, "--mcp-command", command, "--runtime-api-key", "env:" + KEY_ENV, "--json"], env=env, key=key)
    status = run_client(["runtimes", "status", "collabo-codex", "--json"], env=env, key=key)
    write_json(RUNTIME / "status.json", status)
    return {k: status.get(k) for k in ["process_running", "healthy", "ready", "ui_url", "remote_error"]}


def bind_desktop(anchor=None):
    pipe = os.environ.get("CODEX_APP_TOOLS_PIPE_PATH")
    anchor = anchor or os.environ.get("CODEX_THREAD_ID")
    if not pipe or not anchor:
        raise ValueError("Run bind-desktop from a local Codex chat; provide --anchor-thread-id for that real chat if needed. See docs/desktop-bridge.md")
    if not re.fullmatch(r"[a-fA-F0-9-]{36}", anchor):
        raise ValueError("Use the actual local Codex chat ID")
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    candidates = list((codex_home / "plugins/cache/openai-bundled/codex-app-tools").glob("*/server.mjs"))
    if not candidates:
        raise ValueError("The desktop's official codex-app-tools plugin was not found")
    candidates.sort(key=lambda p: [int(n) for n in re.findall(r"\d+", p.parent.name)], reverse=True)
    node = os.environ.get("CODEX_MCP_NODE_PATH") or shutil.which("node")
    if not node:
        bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
        node = str(bundled) if bundled.exists() else None
    if not node:
        raise ValueError("Node.js was not found; install Node or run this command from local Codex")
    write_json(RUNTIME / "desktop-bridge.json", {"node": node, "server": str(candidates[0]),
               "pipe_path": pipe, "anchor_thread_id": anchor})
    return {"desktop_bound": True, "restart_tunnel_required": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    install = sub.add_parser("install-tunnel"); install.add_argument("--proxy")
    bind = sub.add_parser("bind-desktop"); bind.add_argument("--anchor-thread-id")
    roots = sub.add_parser("set-roots"); roots.add_argument("paths", nargs="*")
    for action in ["connect", "status", "stop", "list-local-projects"]:
        sub.add_parser(action)
    args = parser.parse_args()
    try:
        if args.action == "install-tunnel":
            result = {"installed": install_tunnel(args.proxy)}
        elif args.action == "bind-desktop":
            result = bind_desktop(args.anchor_thread_id)
        elif args.action == "list-local-projects":
            from gateway import DesktopProxy, local_project_records
            async def fetch_projects():
                response = await asyncio.wait_for(DesktopProxy().call_tool("list_projects", {}), timeout=25)
                return {"projects": local_project_records(response)}
            result = asyncio.run(fetch_projects())
        elif args.action == "set-roots":
            config = validate_file_config({**read_json(FILES_CONFIG, {}), "roots": args.paths})
            write_json(FILES_CONFIG, config); result = config
        elif args.action == "connect":
            result = connect_tunnel()
            if not all(result.get(k) for k in ["process_running", "healthy", "ready"]):
                raise ValueError("Tunnel is not locally ready; inspect .runtime/status.json")
        else:
            state = run_client(["runtimes", args.action, "collabo-codex", "--json"])
            result = {k: state.get(k) for k in ["process_running", "healthy", "ready", "runtime_state", "ui_url"]}
        print(json.dumps(result, ensure_ascii=True))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
