# 使用与排错

## 首次准备

1. 安装 Python 3.11 或更新版本，下载仓库到一个固定目录，运行 `Install.cmd`。
2. 在 OpenAI Platform 中创建 Tunnel。Organization 是 Platform 组织，ChatGPT workspace 是使用插件的个人或团队空间，不是本地文件夹，也不是某个代码项目。
3. 创建具备 Tunnels Read + Use 权限的运行密钥。个人用户通常选择自己的身份；服务账号适合由团队管理的长期服务。不要把密钥贴进聊天，也不要把 Admin key 当运行密钥使用。
4. 运行 `Setup.cmd`，输入 Tunnel ID、密钥，按需填写代理并选择文件读取目录，然后点击 Save and connect。
5. 在 ChatGPT 插件设置添加自定义 MCP，选择 Tunnel，使用相同的 Tunnel ID，身份验证选择 No authentication。这里的 No authentication 指 MCP 服务自身的认证方式，Tunnel 连接仍使用你保存的运行密钥。
6. 在普通 Chat 中选择这个插件，调用 `list_roots`，再读取一个普通测试文件。只有这一步成功，才说明 Chat 到本机的完整链路接通。

创建 Tunnel、选择账户空间和安装插件需要用户在账户界面完成。工具负责下载校验、配置生成、密钥本机加密、预检和运行管理。

## 日常操作

日常调整目录请打开 **Permissions.cmd**。这个中文窗口只管理读取权限，与 Tunnel/密钥设置分开：

- 添加目录后立即允许读取；勾选/取消勾选立即保存，无须点击额外保存按钮。
- 取消授权的目录会保留在列表中，可随时重新勾选；也可移除所选项或一键取消全部授权。
- **导入本地项目**：读取桌面已保存的本机项目，一次加入所有现有本地目录并授权其子目录；排除远程和云端项目，需要桌面已绑定并保持打开。
- “重新加载”可同步其他窗口或本机命令行对授权的修改。

生效时点为下一次工具调用；已经开始的读取和已经返回到聊天中的内容不会被撤回。若仍授权了父目录，取消子目录勾选不会覆盖父目录权限。导入只发生在点击时，之后新增项目不会被静默授权。

重新打开 `Setup.cmd` 可以修改目录、代理或密钥。密钥框留空表示沿用已保存密钥；已保存密钥不会回显。移除目录后保存，下一次文件工具调用即撤销该目录读取权。已经返回到聊天的内容不会被撤回。

命令行操作须在仓库目录执行：

```powershell
# 状态、停止、再次连接
.\.venv\Scripts\python.exe tools\manage.py status
.\.venv\Scripts\python.exe tools\manage.py stop
.\.venv\Scripts\python.exe tools\manage.py connect

# 修改白名单；不传目录就是全部撤销
.\.venv\Scripts\python.exe tools\manage.py set-roots "D:\Documents"
.\.venv\Scripts\python.exe tools\manage.py set-roots
```

这版不设置开机自启。电脑睡眠、代理停止或桌面关闭后，应先恢复这些条件，再检查状态和重新连接。

## 在指定项目下工作

先在桌面客户端添加本地项目，再完成 [桌面绑定](desktop-bridge.md)。在普通 Chat 中让工具列出本地项目，按返回的路径确认目标，然后明确要求创建任务：

> 在刚才选中的本地项目下新建任务。目标：按已确认提纲写一份方案。输入：inputs 目录的材料。限制：不修改原文件。交付：outputs 目录中的文档，并在任务回复中给出路径。

保留返回的任务 ID，后续可读取进度或明确要求向该任务补充指令。聊天之间不会自动共享全部历史或记忆；请在任务提示中带上已确认的目标、材料路径、限制和验收条件。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| 找不到 Python／环境未安装 | 安装 Python 3.11+，重新运行 Install.cmd；也可给 Install.ps1 传入 -PythonPath |
| 下载失败 | 在 Setup 填可用 HTTP(S) 代理；本机代理应先启动，再安装或连接 |
| Tunnel 未 ready | 检查 Tunnel ID、运行密钥权限和工作区授权；诊断在 `.runtime/doctor.json`、`status.json`、`last-error.json` |
| 本机 ready，但 Chat 没工具 | 检查账户是否允许自定义 MCP、插件是否安装并在当前 Chat 选中；刷新插件工具发现 |
| 只有四个文件工具 | 桌面桥接尚未绑定或失效；按绑定指南重新绑定，再重连并刷新插件 |
| 目录越界／无可用根目录 | 本机 Setup 添加目录并保存；Chat 无法自行扩权 |
| 文档文字不完整 | 检查 `next_offset` 和 `extraction_limited`；图片/扫描 PDF 需要另做 OCR，旧 Office 格式先另存为新格式 |
| 密钥无法解密 | DPAPI 绑定 Windows 用户；换电脑或用户后重新输入密钥 |

诊断文件可能包含本机目录、Tunnel 标识或其他账户元数据。提交问题前先删去这些内容，始终不提交 `.runtime`。
