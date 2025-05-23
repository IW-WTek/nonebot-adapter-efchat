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
> 1. **账号密码登录**（即非官方的野生机器人）
> 2. **发送语音**
> 3. **其他有可能危害聊天室安全的功能**

---

## 🚀 特性
- 🔌 **NoneBot 适配**，可直接集成到 NoneBot 插件系统，实现灵活的机器人开发
- 📡 **自动处理 EFChat 事件**，支持房间消息、私聊、系统通知等

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

在 `.env` 或配置文件中添加：
```ini
DRIVER=~websockets

COMMAND_START=[""]

NICKNAME=[]

LOG_LEVEL=INFO

EFCHAT_name=xxxx
# Bot 名称
EFCHAT_CHANNEL="PublicR"
# Bot 活跃的 Channel
EFCHAT_HEAD="https://efchat.melon.fish/imgs/ava.png"
# Bot 头像地址
EFCHAT_TOKEN=xxxx
# 你的认证 token
```

> ⚠️ **暂不支持同时连接多个房间**

---

## 📖 API 参考

### `MessageEvent(Event)`
EFChat 消息基本模型：
- `event.message`：消息内容
- `event.trip`: 加密身份标识
- `event.self_id`: Bot 名称
- `event.nick`：发送者的用户 ID
- `event.channel`：聊天室名称

### `send()`
根据 **消息类型** 选择 `send_chat_message()` 或 `send_whisper_message()`：
```python
await bot.send(event, message="你好！", at_sender=True, reply_message=False)
```
> **参数说明**：
> - `event`: 消息事件（`ChannelMessageEvent` 或 `WhisperMessageEvent`）
> - `message`: 要发送的内容（`str` 或 `Message`）
> - `at_sender`: 是否 @ 发送者
> - `reply_message`: 是否回复原消息内容

---

### `send_chat_message()`
发送消息到 **当前房间**：
```python
await bot.send_chat_message(event, message="Hello!", show=True, at_sender=False, reply_message=False)
```
> **参数说明**：
> - `event`: 房间消息事件
> - `message`: 要发送的内容（`str` 或 `Message`）
> - `show`: 是否在聊天记录中显示 (`True` 显示，`False` 隐藏)
> - `at_sender`: 是否 @ 发送者
> - `reply_message`: 是否回复原消息内容

---

### `send_whisper_message()`
发送 **私聊消息** 给指定用户：
```python
await bot.send_whisper_message(event, message="Hello EFChat!", at_sender=False, reply_message=False)
```
> **参数说明**：
> - `event`: 私聊消息事件
> - `message`: 要发送的内容（`str` 或 `Message`）
> - `at_sender`: 是否 @ 发送者
> - `reply_message`: 是否回复原消息内容

---

### `move()`
移动 Bot 到指定房间：
```python
await bot.move("PrivateRoom")
```

---

### `change_nick()`
修改 Bot 名称：
```python
await bot.change_nick("EFChatBot")
```

---

### `get_chat_history()`
获取指定数量的 **历史聊天记录**：
```python
await bot.get_chat_history(num=50)
```

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

---

## 🔨 开发与贡献
欢迎贡献代码！请遵循以下流程：
1. **Fork 本仓库** 并克隆代码。
2. **提交 Pull Request**，描述你的改动。

---

## 📜 许可证
本项目基于 **MIT 许可证** 开源，你可以自由使用和修改。
