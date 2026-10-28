"""Keep runtime keys in the current user's operating-system credential store."""
import base64
import sys
import uuid

from configuration import RUNTIME, read_json, write_json

KEYCHAIN_SERVICE = "Collabo-codex"


def mac_keyring():
    from keyring.backends.macOS import Keyring
    return Keyring()


def save_runtime_key(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("请输入运行密钥")
    value = value.strip()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        import win32crypt
        encrypted = win32crypt.CryptProtectData(value.encode("utf-8"), None, None, None, None, 0)
        (RUNTIME / "runtime-key.dpapi").write_text(base64.b64encode(encrypted).decode("ascii"), encoding="ascii")
    elif sys.platform == "darwin":
        metadata = read_json(RUNTIME / "keychain.json", {})
        account = metadata.get("account") or str(uuid.uuid4())
        try:
            mac_keyring().set_password(KEYCHAIN_SERVICE, account, value)
        except Exception:
            raise ValueError("密钥保存失败，请解锁 Mac 登录钥匙串后重试") from None
        write_json(RUNTIME / "keychain.json", {"account": account})
    else:
        raise ValueError("密钥配置支持 Windows 和 macOS")


def load_runtime_key():
    if sys.platform == "win32":
        import win32crypt
        encrypted = base64.b64decode((RUNTIME / "runtime-key.dpapi").read_text(encoding="ascii").strip(), validate=True)
        return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode("utf-8")
    if sys.platform == "darwin":
        account = read_json(RUNTIME / "keychain.json", {}).get("account")
        if not account:
            raise ValueError("请先在 Setup 中填写运行密钥")
        try:
            value = mac_keyring().get_password(KEYCHAIN_SERVICE, account)
        except Exception:
            raise ValueError("读取密钥失败，请解锁 Mac 登录钥匙串后重试") from None
        if not value:
            raise ValueError("请在 Setup 中重新填写运行密钥")
        return value
    raise ValueError("密钥配置支持 Windows 和 macOS")
