<p align="center"><img src="assets/icon.png" width="88" alt="Collabo-codex icon"></p>

# Collabo-codex

让 Chat 讨论方案，让本地 Work／Codex 执行任务。通过 MCP 读取你授权的本机目录、提取 Word/PPT 内容，并在桌面指定项目下创建和跟进工作。

Collabo-codex 是本机 MCP 网关：文件读取使用 Microsoft MarkItDown；会话协作复用已安装桌面客户端的官方 `codex-app-tools`；普通 Chat 通过 OpenAI Secure MCP Tunnel 连接本机。

```text
Chat 讨论并确认方案
       ↓ MCP / Secure MCP Tunnel
Collabo-codex（你的电脑）
       ├─ 授权目录：列文件、找文件、读取文档
       └─ 桌面会话：指定本地项目 → 创建任务 → 补充要求 → 读取进度和结果
```

## 能做什么

| 工具 | 用途 |
| --- | --- |
| `list_roots` | 查看用户授权的文件读取目录 |
| `list_files` | 分页浏览目录，返回文件路径、大小和修改时间 |
| `search_files` | 按中文/英文名称、子串或 `*.pptx` 等通配符查找 |
| `read_file` | 分段读取文本，或提取 DOCX、PPTX、XLSX/XLS、PDF 为 Markdown |
| `list_local_projects` | 查看桌面已保存的本地项目和项目 ID |
| `create_work_task` | 将任务创建到用户指定的本地项目下 |
| `list_threads` / `read_thread` | 查询聊天及选定任务的结果 |
| `send_message_to_thread` | 向用户指定的任务补充要求 |
| `wait_threads` / `set_thread_title` | 查询完成状态、修改任务标题 |

新建和发消息需要用户明确提出。工具不会把一次方案讨论自动当作执行指令。窗口之间通过目标、材料路径、限制和交付要求进行交接。

## Windows 快速开始

准备 Python 3.11+、已登录的 ChatGPT/Codex 桌面客户端，以及允许创建自定义 MCP 插件的个人账户或工作区。首次安装需要联网。

1. 下载或克隆本仓库，解压到固定位置。双击 **`Install.cmd`**，安装项目独立环境。
2. 在 [OpenAI Tunnel 设置](https://platform.openai.com/settings/organization/tunnels) 创建 Tunnel，关联自己的 Platform 组织和客户端使用的 ChatGPT 工作区；记录 Tunnel ID。
3. 在 [Runtime API keys](https://platform.openai.com/settings/organization/api-keys) 创建运行密钥。个人使用可选自己为所有者，确保该身份具有 **Tunnels Read + Use**。不要使用 Admin key。
4. 双击 **`Setup.cmd`**：填写 Tunnel ID 和运行密钥；有需要再填 HTTP 代理；用 **Add folder** 选择允许读取的目录。点击 **Save and connect**。
5. 工具自动下载并校验官方 Windows Tunnel 客户端，生成配置、执行预检并启动。看到本机 ready 后，在 ChatGPT 的 **Plugins → 添加自定义 MCP server** 中选择 **Tunnel**，选择同一个 Tunnel ID，身份验证选 **No authentication**，创建并安装插件。
6. 在客户端普通 Chat 选择插件，先说“列出允许读取的目录”，再读取一个合成或普通测试文件，确认完整连接成功。

网页可能用于一次性账户设置和插件配置；日常使用可以继续留在客户端 Chat。官方账户权限和插件授权仍由用户自己操作。

### 启用桌面任务协作

文件工具可先独立使用。要使用项目/会话工具，还需把桌面的官方 MCP 连接绑定到本地会话。请按照 [桌面绑定指南](docs/desktop-bridge.md) 在一个本地 Codex 对话中运行绑定命令，再重新连接隧道并刷新插件工具。

这是当前桌面版本的适配：**没有随仓库分发 OpenAI 的专有插件，也没有公开稳定的 ChatGPT Work REST API**。桌面须保持打开；重启、升级或 IPC 端点变化后可能需要重新绑定。绑定失效时文件工具继续可用，会话工具不会假装成功。

### 把任务放到指定本地项目

先让 Chat 调用 `list_local_projects`，选择其中一个项目。然后可以说：

> 在刚才选中的本地项目下新建任务：按已确认的大纲撰写文档，材料在项目的 inputs 目录，交付到 outputs，不修改原始材料。

`create_work_task` 只接受当前本机已注册的项目 ID，再次查询项目后将 `projectId + environment.local` 传给桌面原生新建接口。它会拒绝未知、远程或云端项目，不把任务静默创建到默认目录。需要新目录时，先在桌面客户端将它添加为本地项目。

本地执行聊天的界面名称/模式由桌面当前版本决定；本工具不强制改写 UI 模式，也不把 API 创建的云端会话冒充本地 Work。

## 自定义文件读取权限

`Setup.cmd` 中的目录列表就是读取白名单，包括每个目录的子目录。**默认列表为空，代表不允许读取任何目录。** 可随时 Add folder / Remove 后 Save settings；文件 MCP 在下一次调用时重新加载，无需重启。

也可以在本机命令行设置（将示例替换成自己的目录）：

```powershell
.\.venv\Scripts\python.exe tools\manage.py set-roots "D:\Documents" "E:\Research"
# 清空白名单：
.\.venv\Scripts\python.exe tools\manage.py set-roots
```

权限只允许在本机配置工具/文件中修改，Chat 没有扩大自己文件权限的工具。该白名单约束文件读取服务；Work/Codex 执行任务的权限由桌面客户端独立管理。

## 文档读取

- DOCX：标题、正文、表格；PPTX：幻灯片文字和演讲者备注。
- XLSX/XLS：表格文字；PDF：可提取文本。
- 文本、代码、CSV、JSON 等支持 UTF-8、带 BOM 的 UTF-16、GB18030，可指定编码。
- 旧 `.doc` / `.ppt` 需要先转换为 `.docx` / `.pptx`。
- 不提供 OCR 或图像理解；Markdown 不保证保留视觉版式、图表和图片。

默认单文件 64 MB，Office 展开内容 256 MB，转换 45 秒超时。读取长内容使用 `next_offset`；搜索结果的 `incomplete` 为 true 时，应缩小范围，不能断言其他位置没有文件。

## 配置和密钥放在哪里

所有用户配置、加密密钥、桌面绑定和诊断均位于忽略提交的 `.runtime/`；下载的官方二进制在 `bin/`。配置工具用 Windows 当前用户的 DPAPI 加密运行密钥，只在启动 Tunnel 时解密到子进程环境，不写入源码或明文参数。

文件工具没有写入/执行接口；拒绝 URL、UNC、备用数据流、目录越界、常见凭据文件和 `.runtime`。搜索不跟随目录联接/符号链接，显式读取也会检查解析后的目标。目录授权不是对所有敏感文件的自动识别，选择范围时请按实际需要授权。

完整操作和排错见 [使用指南](docs/usage.md)、[桌面绑定](docs/desktop-bridge.md)、[能力与验证状态](docs/validation.md)。

## 开发与测试

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

纯 stdio 使用：`.\.venv\Scripts\python.exe gateway.py`。仅文件服务：`.\.venv\Scripts\python.exe server.py`。配置格式见 `config.example.json`；实际文件配置为 `.runtime/files.json`。

## 依赖与许可

本仓库代码为 MIT。依赖 [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)、[Microsoft MarkItDown](https://github.com/microsoft/markitdown)；配置工具下载 [OpenAI tunnel-client](https://github.com/openai/tunnel-client) 官方发布包并保留其中许可文件。已安装桌面的官方插件由用户本机提供，适用其原有许可，不属于本仓库 MIT 授权范围。
