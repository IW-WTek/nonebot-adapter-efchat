<p align="center">
  <a href="https://nonebot.dev/"><img src="https://nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# NoneBot-Adapter-EFChat

_✨ NoneBot2 EFChat 协议适配 / EFChat Protocol Adapter for NoneBot2 ✨_

</div>

## EFChat适配器简述

EFChat Adapter 是一个适用于 **[EFChat聊天室](https://efchat.melon.fish)** 的 **NoneBot 适配器**，可以轻松地在 EFChat 聊天室中开发机器人，并使用 NoneBot 生态来构建聊天机器人。

> [!IMPORTANT]
>
> 为了避免造成不必要的麻烦，本适配器不会支持以下功能：
> 1. **其他有可能危害聊天室安全的功能**

---

## 🚀 特性
- 🔌 **NoneBot 适配**，可直接集成到 NoneBot 插件系统，实现灵活的机器人开发
- 📡 **自动处理 EFChat 事件**，支持房间消息、私聊、系统通知等
- ✨ **暂不支持多Bot**， 暂不支持同时运行并管理多个bot

---

## 📦 安装
```bash
pip install nonebot-adapter-efchat
```
---

## 🔧 配置
在 `bot.py` 中启用 EFChat 适配器：
```python
from nonebot import get_driver
from nonebot.adapters.efchat import Adapter

driver = get_driver()
driver.register_adapter(Adapter)
```

在 `.env` 文件中添加：
```ini
DRIVER=~websockets

EFCHAT_BOTS = '
[
    {
        "nick": "EFChatBot",
        "password": "",
        "channel": "PublicR",
        "head": "https://efchat.melon.fish/imgs/ava.png",
        "token": ""
    }
]
'

EFCHAT_IGNORE_SELF=True
# 忽略Bot自身的消息，默认启用
```
* 配置项`token`是必填项
* 如果Bot将会拥有管理员权限，请提供`password`字段以确保账号安全
- `nick`是bot账号，同时也是在聊天室里显示的昵称
- `channel`是Bot活跃的房间名称
- `head`是Bot的头像url地址

> ⚠️ **暂不支持一个bot同时连接多个房间**

---

## [📖 API 参考](api.md)

---

## 💬 使用示例

### **消息回显**
在 `plugins/echo.py` 中创建一个简单的回显插件：
```python
from nonebot import on_message
from nonebot.adapters.efchat import MessageEvent

echo = on_message()

@echo.handle()
async def handle_echo(event: MessageEvent):
    await echo.send(f"你发送的消息是: {event.get_message()}")
```

机器人发送的消息默认不保存到聊天记录，如果需要保存，请在发送消息时传入`show=True`

例如
```py
await matcher.send("xxx", show=True)
```
---

## 🔨 开发与贡献
欢迎贡献代码！请遵循以下流程：
1. **Fork 本仓库** 并克隆代码。
2. **提交 Pull Request**，描述你的改动。

---

## 📜 许可证
本项目基于 **MIT 许可证** 开源，你可以自由使用和修改。
