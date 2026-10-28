# 日常使用指南

首次安装和配置见 [README](../README.md)。

## 三个常用入口

| 用途 | Windows | Mac |
| --- | --- | --- |
| 首次安装，或更新后安装组件 | Install.cmd | Install.command |
| 填写连接信息、修改密钥或重新连接 | Setup.cmd | Setup.command |
| 随时调整允许读取的目录 | Permissions.cmd | Permissions.command |

## 修改目录权限

Windows 打开 **Permissions.cmd**，Mac 打开 **Permissions.command**，直接添加、勾选或取消勾选。每次操作立即保存，下一次读取生效。

点击 **导入本地项目**，一次加入桌面已保存的所有本机项目目录及其子目录。先完成 [本地项目连接](desktop-bridge.md)，并保持桌面客户端打开。

取消勾选的目录会留在列表中，方便下次恢复。按项目控制权限时，只勾选项目目录，并取消更上层的大目录。新增项目后，再点一次导入。

## 重新连接

Windows 打开 **Setup.cmd**，Mac 打开 **Setup.command**。密钥框留空，点击 **Save and connect / 保存并连接**，继续使用已保存的密钥。

电脑开机后，或网络恢复后，可以用这个方法重新连接。

## 更新到新版本

Windows：在 Collabo-codex 文件夹中打开 PowerShell，依次运行：

```powershell
.\.venv\Scripts\python.exe tools\manage.py stop
git pull --ff-only
.\Install.cmd
.\.venv\Scripts\python.exe tools\manage.py connect
```

Mac：在终端进入 Collabo-codex 文件夹，依次运行：

```bash
./.venv/bin/python tools/manage.py stop
git pull --ff-only
bash Install.command
./.venv/bin/python tools/manage.py connect
```

安装结束后，在 ChatGPT 插件详情中点击 **Refresh / 刷新**，再开一个新 Chat 使用。密钥和目录设置会保留。

## 常见问题

| 遇到的情况 | 怎么处理 |
| --- | --- |
| Install 找不到 Python | 从 python.org 安装 Python 3.12 或更新版本，再运行对应的安装文件 |
| Mac 双击入口没有启动 | 在终端进入本文件夹，运行 `bash Install.command`、`bash Setup.command` 或 `bash Permissions.command` |
| Mac 提示钥匙串锁定 | 解锁登录钥匙串，再打开 Setup 保存或连接 |
| 下载或连接失败 | 先启动正在使用的代理，再检查 Setup 中的代理地址 |
| 插件连接失败 | 在 Setup 检查 Tunnel ID 和运行密钥，然后重新连接 |
| Chat 找不到工具 | 确认插件已安装，在新 Chat 中输入 `@` 选择它 |
| 读取文件提示目录未授权 | 在 Permissions 中勾选文件所在目录 |
| 本地项目列表读取失败 | 重新执行本地项目连接步骤 |
| Word 或 PPT 读取失败 | 在 Office 中另存为 `.docx` 或 `.pptx` 后再读取 |
| 扫描 PDF 读不到文字 | 先把 PDF 转成可选中文字的版本 |
| 换电脑或系统用户后密钥失效 | 在 Setup 中重新填写运行密钥 |
