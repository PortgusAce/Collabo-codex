<p align="center"><img src="assets/icon.png" width="88" alt="Collabo-codex"></p>

# Collabo-codex

在 Chat 里讨论方案、读取电脑上的文件，再把任务交给指定的本地项目执行。

## 能做什么

- 浏览文件夹，按名称寻找文件。
- 读取文本、代码、Word、PPT、Excel 和文字版 PDF。
- 列出本地项目，在选定项目下新建执行任务。
- 查看任务进度和结果，给已有任务补充要求。
- 随时调整允许读取的目录，一键导入所有本地项目目录。

## 第一次怎么配置

准备一台 Windows 电脑，安装 Python 3.11 或更新版本，并登录 ChatGPT/Codex 桌面客户端。

### 1. 安装

下载本仓库，解压到固定位置，双击 **Install.cmd**，等待安装完成。

### 2. 创建连接和密钥

1. 打开 [OpenAI Tunnel 设置](https://platform.openai.com/settings/organization/tunnels)，创建一个 Tunnel。它负责连接 ChatGPT 和你的电脑。
2. 选择自己的组织，以及使用插件的 ChatGPT 个人或团队空间，记下 **Tunnel ID**。
3. 打开 [API keys](https://platform.openai.com/settings/organization/api-keys)，创建运行密钥。个人使用可选自己为所有者，权限勾选 **Tunnels Read + Use**。

### 3. 在本机填写配置

双击 **Setup.cmd**，填写：

| 项目 | 填什么 |
| --- | --- |
| Tunnel ID | 上一步创建的 ID |
| Runtime API key | 上一步创建的运行密钥 |
| Proxy | 按需填写正在使用的 HTTP 代理地址 |
| 目录列表 | 点击 Add folder，选择允许读取的目录 |

点击 **Save and connect**。工具会自动下载连接程序并启动。密钥只需在这个本机窗口填写一次。

### 4. 添加到 ChatGPT

1. 打开 [Plugins](https://chatgpt.com/plugins)，点击加号，选择 **Add custom MCP server**。
2. 名称填写 **Collabo-codex**，连接方式选择 **Tunnel**，选中刚才的 Tunnel ID。
3. 身份验证选择 **No authentication**，创建并安装插件。
4. 新建普通 Chat，输入 `@` 选择插件，发送：“列出允许读取的目录”。

### 5. 连接本地项目

使用新建任务、查看进度和导入项目目录前，按 [本地项目连接步骤](docs/desktop-bridge.md) 完成一次设置。

## 日常怎么使用

### 读取文件

在 Chat 中选择插件，直接说：

> 在允许读取的目录里，按名称寻找“研究方案”。
>
> 读取刚才找到的 Word，整理主要内容和表格。
>
> 读取这份 PPT 的文字和演讲者备注。

Word 使用 `.docx`，PPT 使用 `.pptx`。旧版文件先在 Office 中另存为这两种格式。扫描版 PDF 先转成可选中文字的版本。

### 让本地项目执行任务

> 列出我的本地项目。
>
> 在选中的项目下新建任务：按刚才确认的大纲写一份方案，材料在 inputs 目录，完成的文档放到 outputs 目录。
>
> 查看这个任务的进度。
>
> 给这个任务补充要求：增加一页执行计划。

交接任务时，写清目标、材料位置、具体要求和交付位置。使用期间保持桌面客户端打开。

### 调整读取目录

双击 **Permissions.cmd** 打开目录权限窗口：

- **添加目录**：选择一个文件夹并允许读取。
- **导入本地项目**：一次加入桌面已保存的所有本机项目目录，包含子目录。
- **勾选 / 取消勾选**：开启或撤销该目录的读取权限。
- **移除所选项 / 全部取消授权**：清理目录列表或暂停全部读取。

每次操作立即保存，下一次读取生效。修改目录时直接使用这个窗口，原有连接和密钥继续沿用。

按项目控制权限时，只勾选需要的项目目录，并取消更上层的大目录。之后新增的项目，再点一次“导入本地项目”即可加入。

重新连接、更新和常见问题见 [日常使用指南](docs/usage.md)。

代码采用 [MIT 许可](LICENSE)。文档提取使用 [Microsoft MarkItDown](https://github.com/microsoft/markitdown)。
