"""macOS setup and directory windows, using Python's bundled Tk interface."""
from pathlib import Path
import argparse
import queue
import re
import sys
import threading
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from configuration import RUNTIME, read_json, write_json, validate_file_config
from credentials import save_runtime_key
from tools import manage


def save_connection(tunnel_id, proxy, key=""):
    tunnel_id, proxy = tunnel_id.strip(), proxy.strip()
    if not re.fullmatch(r"tunnel_(?:[a-z0-9]{4}_)?[a-z0-9]{32}", tunnel_id):
        raise ValueError("请填写正确的 Tunnel ID")
    if proxy:
        parsed = urlsplit(proxy)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or not parsed.port:
            raise ValueError("代理地址请填写为 http://地址:端口")
    if key.strip():
        save_runtime_key(key)
    write_json(RUNTIME / "tunnel.json", {"tunnel_id": tunnel_id, "proxy": proxy})


def directory_selection():
    active = validate_file_config(read_json(RUNTIME / "files.json", {"roots": []}))["roots"]
    try:
        remembered = read_json(RUNTIME / "directories-ui.json", {}).get("directories", [])
    except (ValueError, OSError):
        remembered = []
    if not isinstance(remembered, list) or not all(isinstance(p, str) for p in remembered):
        remembered = []
    choices = validate_file_config({"roots": list(dict.fromkeys(active + remembered))})["roots"]
    return choices, active


def save_directories(choices, active):
    choices = validate_file_config({"roots": choices})["roots"]
    config = validate_file_config({**read_json(RUNTIME / "files.json", {}), "roots": active})
    if not set(config["roots"]).issubset(choices):
        raise ValueError("请从目录列表中选择授权目录")
    write_json(RUNTIME / "directories-ui.json", {"directories": choices})
    write_json(RUNTIME / "files.json", config)


def import_projects(projects):
    choices, active = directory_selection()
    for project in projects:
        path = project.get("path")
        if project.get("host_id") != "local" or not isinstance(path, str) or path.startswith(("\\\\", "//")):
            continue
        if not Path(path).is_absolute() or not Path(path).is_dir():
            continue
        normalized = validate_file_config({"roots": [path]})["roots"][0]
        if normalized not in choices:
            choices.append(normalized)
        if normalized not in active:
            active.append(normalized)
    save_directories(choices, active)


class Window:
    def __init__(self, root):
        from tkinter import ttk
        self.root = root
        self.pending = queue.Queue()
        self.frame = ttk.Frame(root, padding=18)
        self.frame.pack(fill="both", expand=True)
        root.minsize(740, 420)
        root.after(100, self.poll)

    def error(self, exc):
        from tkinter import messagebox
        messagebox.showerror("Collabo-codex", str(exc), parent=self.root)

    def run(self, work, done):
        def worker():
            try:
                self.pending.put((done, work(), None))
            except Exception as exc:
                self.pending.put((done, None, exc))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                done, result, error = self.pending.get_nowait()
                done(result, error)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)


class Permissions(Window):
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk
        super().__init__(root)
        root.title("Collabo-codex · 目录读取权限")
        ttk.Label(self.frame, text="勾选即授权，取消勾选即撤销；每次操作立即保存。").pack(anchor="w")
        ttk.Label(self.frame, text="按项目控制权限时，只勾选项目目录，并取消更上层的大目录。").pack(anchor="w", pady=(5, 12))
        buttons = ttk.Frame(self.frame)
        buttons.pack(fill="x", pady=(0, 10))
        ttk.Button(buttons, text="添加目录", command=self.add).pack(side="left", padx=(0, 8))
        self.import_button = ttk.Button(buttons, text="导入本地项目", command=self.import_all)
        self.import_button.pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="全部取消授权", command=self.revoke).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="重新加载", command=self.reload).pack(side="left")
        box = ttk.Frame(self.frame)
        box.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(box, highlightthickness=0, height=260)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.rows = ttk.Frame(self.canvas)
        self.row_window = self.canvas.create_window((0, 0), window=self.rows, anchor="nw")
        self.rows.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.row_window, width=event.width))
        self.status = tk.StringVar()
        ttk.Label(self.frame, textvariable=self.status, wraplength=700).pack(anchor="w", pady=(12, 0))
        self.reload()

    def reload(self):
        import tkinter as tk
        from tkinter import ttk
        try:
            self.choices, self.active = directory_selection()
            for widget in self.rows.winfo_children():
                widget.destroy()
            for path in self.choices:
                row = ttk.Frame(self.rows)
                row.pack(fill="x", pady=3)
                enabled = tk.BooleanVar(value=path in self.active)
                ttk.Checkbutton(row, text=path, variable=enabled, command=lambda p=path, v=enabled: self.toggle(p, v)).pack(side="left", fill="x", expand=True)
                ttk.Button(row, text="移除", width=5, command=lambda p=path: self.remove(p)).pack(side="right", padx=5)
            self.status.set(f"允许读取 {len(self.active)} 个目录。修改后立即保存，下一次读取生效。")
        except Exception as exc:
            self.error(exc)

    def save(self, choices, active):
        try:
            save_directories(choices, active)
        except Exception as exc:
            self.error(exc)
        self.reload()

    def toggle(self, path, enabled):
        active = [p for p in self.active if p != path]
        if enabled.get():
            active.append(path)
        self.save(self.choices, active)

    def add(self):
        from tkinter import filedialog
        selected = filedialog.askdirectory(parent=self.root, title="选择允许读取的目录")
        if selected:
            path = str(Path(selected).resolve())
            self.save(list(dict.fromkeys(self.choices + [path])), list(dict.fromkeys(self.active + [path])))

    def remove(self, path):
        self.save([p for p in self.choices if p != path], [p for p in self.active if p != path])

    def revoke(self):
        self.save(self.choices, [])

    def import_all(self):
        self.import_button.state(["disabled"])
        self.status.set("正在读取桌面已保存的本地项目…")
        def work():
            import asyncio
            from gateway import DesktopProxy, local_project_records
            async def fetch():
                return local_project_records(await asyncio.wait_for(DesktopProxy().call_tool("list_projects", {}), timeout=25))
            return asyncio.run(fetch())
        def done(result, error):
            self.import_button.state(["!disabled"])
            try:
                if error:
                    raise ValueError("读取项目失败，请保持桌面打开并重新连接本地项目")
                import_projects(result)
            except Exception as exc:
                self.error(exc)
            self.reload()
        self.run(work, done)


class Setup(Window):
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk
        super().__init__(root)
        root.title("Collabo-codex · 首次配置")
        saved = read_json(RUNTIME / "tunnel.json", {})
        ttk.Label(self.frame, text="填入连接信息，密钥保存在 Mac 钥匙串中。").pack(anchor="w", pady=(0, 16))
        self.fields = {}
        for label, name, value in [("Tunnel ID", "tunnel_id", saved.get("tunnel_id", "")), ("运行密钥", "key", ""), ("代理地址（按需填写）", "proxy", saved.get("proxy", ""))]:
            ttk.Label(self.frame, text=label).pack(anchor="w")
            entry = ttk.Entry(self.frame, show="•" if name == "key" else "")
            entry.insert(0, value)
            entry.pack(fill="x", pady=(3, 12))
            self.fields[name] = entry
        ttk.Label(self.frame, text="密钥留空时，继续使用已保存的密钥。").pack(anchor="w", pady=(0, 14))
        buttons = ttk.Frame(self.frame)
        buttons.pack(fill="x")
        self.save_button = ttk.Button(buttons, text="保存配置", command=self.save)
        self.save_button.pack(side="left", padx=(0, 10))
        self.connect_button = ttk.Button(buttons, text="保存并连接", command=self.connect)
        self.connect_button.pack(side="left", padx=(0, 10))
        ttk.Button(buttons, text="管理目录权限", command=lambda: Permissions(tk.Toplevel(root))).pack(side="left")
        self.status = tk.StringVar(value="首次使用请先填写密钥，再选择允许读取的目录。")
        ttk.Label(self.frame, textvariable=self.status, wraplength=700).pack(anchor="w", pady=16)

    def save(self):
        try:
            save_connection(*(self.fields[name].get() for name in ["tunnel_id", "proxy", "key"]))
            self.fields["key"].delete(0, "end")
            self.status.set("配置已保存。")
            return True
        except Exception as exc:
            self.error(exc)
            return False

    def connect(self):
        if not self.save():
            return
        self.save_button.state(["disabled"])
        self.connect_button.state(["disabled"])
        self.status.set("正在检查连接程序并启动，请稍候…")
        def work():
            try:
                manage.client_path()
            except ValueError:
                manage.install_tunnel(read_json(RUNTIME / "tunnel.json")["proxy"] or None)
            result = manage.connect_tunnel()
            if not all(result.get(k) for k in ["process_running", "healthy", "ready"]):
                raise ValueError("连接尚未就绪，请检查连接信息后重试")
            return result
        def done(result, error):
            self.save_button.state(["!disabled"])
            self.connect_button.state(["!disabled"])
            if error:
                self.status.set("连接失败。")
                self.error(error)
            else:
                self.status.set("已连接。接下来在 ChatGPT Plugins 中添加这个 Tunnel，并选择插件使用。")
        self.run(work, done)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["setup", "permissions"])
    parser.add_argument("--check-ui", action="store_true")
    args = parser.parse_args(argv)
    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception:
        print("请安装 python.org 提供的 Python 3.12 或更新版本，再运行 Install.command。", file=sys.stderr)
        return 1
    if args.check_ui:
        root.withdraw()
    (Setup if args.mode == "setup" else Permissions)(root)
    if args.check_ui:
        root.update_idletasks()
        root.destroy()
        print("Window loaded")
    else:
        root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
