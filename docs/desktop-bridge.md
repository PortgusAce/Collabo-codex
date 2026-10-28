# 连接本地项目

完成这一步后，Chat 就能列出桌面里的本地项目、在指定项目下创建任务，并查看进度。

## 第一次连接

1. 在桌面客户端中添加要使用的本地项目，选择它所在的文件夹。
2. 新建一个本地 Codex 聊天，打开 Collabo-codex 所在目录。
3. 把下面这句话发给它：

> 请在 Collabo-codex 目录里运行下面的命令，连接当前桌面的本地项目。第一条命令如果需要聊天 ID，请使用当前本地聊天的真实 ID。

Windows：

```powershell
.\.venv\Scripts\python.exe tools\manage.py bind-desktop
.\.venv\Scripts\python.exe tools\manage.py stop
.\.venv\Scripts\python.exe tools\manage.py connect
```

Mac：

```bash
./.venv/bin/python tools/manage.py bind-desktop
./.venv/bin/python tools/manage.py stop
./.venv/bin/python tools/manage.py connect
```

4. 回到 ChatGPT 的插件详情，点击 **Refresh / 刷新**。
5. 新建普通 Chat，输入 `@` 选择插件，发送：“列出我的本地项目”。

## 创建和跟进任务

先列出项目，按名称和目录选中目标，再提出任务。例如：

> 在选中的项目下新建任务：读取 inputs 目录的材料，按已确认大纲写方案，文档放在 outputs 目录。

接着可以说：

> 查看刚才任务的进度。
>
> 给刚才的任务补充要求：最后增加一份检查清单。

新文件夹先添加为桌面的本地项目，再在 Chat 中选择它。交接任务时写清目标、材料位置、具体要求和交付位置。

## 日常使用

- 使用项目功能时，保持桌面客户端打开。
- 桌面重启或更新后，如果项目列表读取失败，重新执行上面的连接步骤。
- 想批量允许读取项目文件，Windows 打开 **Permissions.cmd**，Mac 打开 **Permissions.command**，点击 **导入本地项目**。
