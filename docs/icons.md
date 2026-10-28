# 图标显示与更新

仓库图标有三个使用位置：

1. 本机配置/权限窗口：使用 `assets/icon.ico`。
2. MCP 服务初始化：`serverInfo.icons` 携带透明 PNG，支持此字段的客户端可使用它。
3. ChatGPT Plugins 中现有插件的头像：属于插件展示资料，不等同于 MCP 工具元信息。

上一版只完成了第一项和 README 展示，因此单纯刷新工具列表不会使已有插件头像自动变更。这版补齐第二项；不保证 ChatGPT 自定义连接会采用 `serverInfo.icons`。

如果插件资料页提供编辑图标/上传入口，选择本仓库的 `assets/icon.png`。如果该入口在你的账户中不可用，不能通过本地修改 PNG 或重连 Tunnel 强制更改账户里的头像。不要为了头像删除现有连接。

正式打包插件时，按 [OpenAI 插件打包文档](https://developers.openai.com/plugins/build/plugins#add-openai-specific-metadata) 在根 `plugin.json` 的 `extensions.com.openai.interface` 中设置：

```json
{
  "displayName": "Collabo-codex",
  "composerIcon": "./assets/icon.png",
  "logo": "./assets/icon.png"
}
```

这是展示字段示例，不是一个完整可安装插件包；现有注册 MCP 的映射还需按官方文档关联真实插件 ID。本仓库继续使用已有 Tunnel，未另建一个只有图标、没有连接的插件。
