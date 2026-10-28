# 桌面会话桥接

文件 MCP 可以独立运行；创建项目任务和管理聊天使用本机已安装的官方 `codex-app-tools`。这属于当前桌面版本的适配，不是公开稳定的 Work API。

## 绑定步骤

1. 保持桌面客户端打开。在一个**本地 Codex 执行聊天**中打开本仓库所在目录。
2. 在该聊天中让 Codex 运行以下命令。命令必须由带有桌面提供的 `CODEX_APP_TOOLS_PIPE_PATH` 环境的工具进程执行；普通外部终端通常没有这个环境。

```powershell
.\.venv\Scripts\python.exe tools\manage.py bind-desktop
```

如果当前环境没有自动提供 `CODEX_THREAD_ID`，传入这个真实本地聊天的 ID：

```powershell
.\.venv\Scripts\python.exe tools\manage.py bind-desktop --anchor-thread-id "<当前本地聊天的真实 UUID>"
```

3. 运行 `tools\manage.py connect` 重新连接隧道；在 ChatGPT 中刷新插件工具发现。绑定成功时，应从四个文件工具变为共十一个工具。
4. 先调用 `list_local_projects` 和 `list_threads` 验证只读连接，再按用户的实际指令创建任务或发送消息。

绑定工具只接受桌面当前提供的 IPC 连接，不扫描或猜测私有端点。绑定信息保存在忽略提交的 `.runtime/desktop-bridge.json`。不要向别人分享这个文件。

## 项目定位

`list_local_projects` 仅返回原生项目列表中 `projectKind=local` 且 `hostId=local` 的项目。`create_work_task` 在创建前再次查询，只有精确匹配的项目 ID 才可执行，随后传入：

```json
{
  "target": {
    "type": "project",
    "projectId": "<用户选定的本机项目 ID>",
    "environment": {"type": "local"}
  }
}
```

原生 `create_thread` 不对外公开，调用者无法通过它绕到云端、远程主机或默认目录。该功能不向桌面项目列表注册任意路径；新目录应先由用户在桌面中添加。

创建结果的界面分类由当前桌面版本控制。此版本支持本地执行聊天，不承诺通过程序强制切换到某个 Work UI，也不实现创建云端 ChatGPT Work 会话。

## 生命周期和授权

桌面重启、插件升级或安装聊天被移除后，连接可能失效，需要重新绑定。桥接初始化失败时，网关仍提供文件工具；若工具列表已缓存，须重新连接隧道和刷新插件。运行中的原生读取/发送失败会返回错误，不返回虚假成功。

创建、发送消息和改标题的原生说明会保留，并补充明确人类授权约束。文件内容和其他聊天的摘要不构成发送指令的授权。发消息会触发目标聊天工作；文件白名单不限制目标聊天自身的执行权限，后者由桌面独立管理。

本仓库只调用用户已安装的官方插件，不复制或再分发其实现。使用官方插件、账户与模型仍须遵守各自条款。
