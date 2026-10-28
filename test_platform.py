import base64
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import pytest

import credentials
from configuration import read_json, write_json
from server import LocalFiles
from tools import manage, macos_ui


@pytest.mark.parametrize("system,machine,target,arch,name", [
    ("darwin", "arm64", "darwin", "arm64", "tunnel-client"),
    ("darwin", "x86_64", "darwin", "amd64", "tunnel-client"),
    ("win32", "AMD64", "windows", "amd64", "tunnel-client.exe"),
    ("win32", "ARM64", "windows", "arm64", "tunnel-client.exe"),
])
def test_release_selection(system, machine, target, arch, name):
    assert manage.tunnel_target(system, machine) == (target, arch, name)


@pytest.mark.parametrize("system,machine", [("linux", "x86_64"), ("darwin", "unknown")])
def test_unsupported_release(system, machine):
    with pytest.raises(ValueError):
        manage.tunnel_target(system, machine)


def test_macos_command_preserves_paths():
    arguments = ["/Users/example/My Project/.venv/bin/python", "/Users/example/a'b $c/项目/gateway.py"]
    assert shlex.split(manage.mcp_command(arguments, "darwin")) == arguments
    assert manage.mcp_command(arguments, "win32") == subprocess.list2cmdline(arguments)


@pytest.mark.parametrize("name,mode", [("../outside", stat.S_IFREG | 0o755), ("link", stat.S_IFLNK | 0o777)])
def test_unsafe_archive_rejected(tmp_path, name, mode):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        item = zipfile.ZipInfo(name)
        item.external_attr = mode << 16
        bundle.writestr(item, "synthetic")
    with pytest.raises(ValueError):
        manage.extract_client(archive, tmp_path / "install")
    assert not (tmp_path / "outside").exists()


def test_macos_download_checksum_and_executable(tmp_path, monkeypatch):
    binary = io.BytesIO()
    with zipfile.ZipFile(binary, "w") as bundle:
        item = zipfile.ZipInfo("tunnel-client")
        item.external_attr = (stat.S_IFREG | 0o755) << 16
        bundle.writestr(item, b"synthetic executable")
    archive_bytes = binary.getvalue()
    digest = hashlib.sha256(archive_bytes).hexdigest()
    requests_seen = []
    class Response:
        def __init__(self, url):
            self.url = "https://github.com/openai/tunnel-client/releases/tag/v9.9.9"
            self.text = digest + "  tunnel-client-v9.9.9-darwin-arm64.zip"
        def raise_for_status(self): pass
        def iter_content(self, _): yield archive_bytes
        def __enter__(self): return self
        def __exit__(self, *_): pass
    class Session:
        def __init__(self): self.headers, self.proxies = {}, {}
        def get(self, url, **_):
            requests_seen.append(url)
            return Response(url)
    import requests
    monkeypatch.setattr(requests, "Session", Session)
    monkeypatch.setattr(manage, "BASE", tmp_path)
    monkeypatch.setattr(manage, "RUNTIME", tmp_path / ".runtime")
    monkeypatch.setattr(manage, "tunnel_target", lambda: ("darwin", "arm64", "tunnel-client"))
    executable = Path(manage.install_tunnel())
    assert executable.name == "tunnel-client"
    assert requests_seen[-1].endswith("tunnel-client-v9.9.9-darwin-arm64.zip")
    assert read_json(tmp_path / ".runtime/tunnel-install.json")["archive_sha256"] == digest
    if os.name != "nt":
        assert os.access(executable, os.X_OK)
    assert Path(manage.install_tunnel()) == executable
    assert len(requests_seen) == 5


def test_macos_desktop_node_discovery(tmp_path, monkeypatch):
    home = tmp_path / "home"
    codex = home / ".codex"
    plugin = codex / "plugins/cache/openai-bundled/codex-app-tools/26.10/server.mjs"
    plugin.parent.mkdir(parents=True)
    plugin.write_text("synthetic")
    node = home / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
    node.parent.mkdir(parents=True)
    node.write_text("synthetic")
    monkeypatch.setenv("CODEX_HOME", str(codex))
    monkeypatch.setenv("CODEX_APP_TOOLS_PIPE_PATH", "/tmp/synthetic.sock")
    monkeypatch.setenv("CODEX_THREAD_ID", "00000000-0000-4000-8000-000000000001")
    monkeypatch.delenv("CODEX_MCP_NODE_PATH", raising=False)
    monkeypatch.setattr(manage, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(manage.shutil, "which", lambda _: None)
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(manage, "RUNTIME", tmp_path / "runtime")
    assert manage.bind_desktop()["desktop_bound"]
    binding = read_json(tmp_path / "runtime/desktop-bridge.json")
    assert binding["node"] == str(node) and binding["server"] == str(plugin)


def test_macos_keychain_roundtrip_has_no_plaintext_file(tmp_path, monkeypatch):
    stored = {}
    ring = SimpleNamespace(set_password=lambda s, a, v: stored.__setitem__((s, a), v),
                           get_password=lambda s, a: stored.get((s, a)))
    monkeypatch.setattr(credentials, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(credentials, "RUNTIME", tmp_path)
    monkeypatch.setattr(credentials, "mac_keyring", lambda: ring)
    credentials.save_runtime_key("synthetic-secret")
    assert credentials.load_runtime_key() == "synthetic-secret"
    account = read_json(tmp_path / "keychain.json")["account"]
    credentials.save_runtime_key("synthetic-replacement")
    assert read_json(tmp_path / "keychain.json")["account"] == account
    assert credentials.load_runtime_key() == "synthetic-replacement"
    assert all(b"synthetic-secret" not in p.read_bytes() and b"synthetic-replacement" not in p.read_bytes() for p in tmp_path.iterdir())


def test_keychain_failure_does_not_save_secret(tmp_path, monkeypatch):
    def fail(*_): raise RuntimeError("synthetic-secret")
    monkeypatch.setattr(credentials, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(credentials, "RUNTIME", tmp_path)
    monkeypatch.setattr(credentials, "mac_keyring", lambda: SimpleNamespace(set_password=fail))
    with pytest.raises(ValueError) as error:
        credentials.save_runtime_key("synthetic-secret")
    assert "synthetic-secret" not in str(error.value)
    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(sys.platform != "win32", reason="Windows credential store")
def test_windows_key_compatible_with_dpapi(tmp_path, monkeypatch):
    monkeypatch.setattr(credentials, "RUNTIME", tmp_path)
    credentials.save_runtime_key("synthetic-windows-key")
    assert credentials.load_runtime_key() == "synthetic-windows-key"
    assert b"synthetic-windows-key" not in base64.b64decode((tmp_path / "runtime-key.dpapi").read_bytes())


@pytest.mark.skipif(sys.platform != "darwin" or os.environ.get("CI") != "true", reason="Isolated macOS CI keychain")
def test_native_macos_keychain(tmp_path, monkeypatch):
    from keyring.backends.macOS import Keyring
    chain = tmp_path / "isolated.keychain-db"
    subprocess.run(["security", "create-keychain", "-p", "synthetic-test-only", str(chain)], check=True, capture_output=True)
    try:
        subprocess.run(["security", "unlock-keychain", "-p", "synthetic-test-only", str(chain)], check=True, capture_output=True)
        ring = Keyring().with_properties(keychain=str(chain))
        monkeypatch.setattr(credentials, "RUNTIME", tmp_path / "runtime")
        monkeypatch.setattr(credentials, "mac_keyring", lambda: ring)
        credentials.save_runtime_key("synthetic-native-roundtrip")
        assert credentials.load_runtime_key() == "synthetic-native-roundtrip"
    finally:
        subprocess.run(["security", "delete-keychain", str(chain)], check=True, capture_output=True)


def test_directory_window_changes_apply_immediately(tmp_path, monkeypatch):
    runtime, folder = tmp_path / "runtime", tmp_path / "folder"
    folder.mkdir()
    sample = folder / "sample.txt"
    sample.write_text("synthetic", encoding="utf-8")
    monkeypatch.setattr(macos_ui, "RUNTIME", runtime)
    write_json(runtime / "files.json", {"roots": [], "max_file_mb": 23})
    server = LocalFiles({"roots": []}, runtime / "files.json")
    macos_ui.save_directories([str(folder)], [str(folder)])
    assert server.read(str(sample))["content"] == "synthetic"
    macos_ui.save_directories([str(folder)], [])
    with pytest.raises(PermissionError): server.read(str(sample))
    assert macos_ui.directory_selection() == ([str(folder)], [])
    assert read_json(runtime / "files.json")["max_file_mb"] == 23


def test_import_projects_excludes_remote_and_reuses_choices(tmp_path, monkeypatch):
    folder = tmp_path / "local"
    other = tmp_path / "remote"
    folder.mkdir(); other.mkdir()
    monkeypatch.setattr(macos_ui, "RUNTIME", tmp_path / "runtime")
    macos_ui.import_projects([
        {"host_id": "local", "path": str(folder)}, {"host_id": "local", "path": str(folder)},
        {"host_id": "remote", "path": str(other)}, {"host_id": "local", "path": "https://example.com"},
        {"host_id": "local", "path": "\\\\host\\share"}])
    assert macos_ui.directory_selection() == ([str(folder)], [str(folder)])


def test_connection_settings_keep_blank_key(tmp_path, monkeypatch):
    monkeypatch.setattr(macos_ui, "RUNTIME", tmp_path)
    calls = []
    monkeypatch.setattr(macos_ui, "save_runtime_key", lambda value: calls.append(value))
    tunnel = "tunnel_" + "1" * 32
    macos_ui.save_connection(tunnel, "http://127.0.0.1:7890", "synthetic")
    macos_ui.save_connection(tunnel, "", "")
    assert calls == ["synthetic"]
    assert read_json(tmp_path / "tunnel.json") == {"tunnel_id": tunnel, "proxy": ""}
    with pytest.raises(ValueError): macos_ui.save_connection("invalid", "")
    with pytest.raises(ValueError): macos_ui.save_connection(tunnel, "file:///tmp")
