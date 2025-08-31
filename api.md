# **EFChat 适配器 API 文档**

## [用户权限说明](permission.md)

## **1. 事件模型**

EFChat 适配器提供了多个事件类型，用于处理消息和通知：

### **MessageEvent(Event)**

表示 EFChat 中的通用消息事件，包括 **房间消息** 和 **私聊消息**。

| 属性            | 说明            |
| --------------- | --------------- |
| `event.message` | 消息内容        |
| `event.trip`    | 加密身份标识    |
| `event.nick`    | 发送者的用户 ID |

---

## **2. 消息发送**

EFChat 适配器提供了以下方法，用于发送消息：

### **2.1 `send(event, message, at_sender=False, reply_message=False)`**

通用消息发送方法

```python
await bot.send(event, message="你好！", at_sender=True, reply_message=False)
```

| 参数            | 类型                      | 说明             |
| --------------- | ------------------------- | ---------------- |
| `event`         | `MessageEvent`            | 事件对象         |
| `message`       | `str` 或 `MessageSegment` | 要发送的消息内容 |
| `at_sender`     | `bool`                    | 是否 @ 发送者    |
| `reply_message` | `bool`                    | 是否回复原消息   |

---

### **2.2 `send_chat_message(message)`**

发送 **房间消息**：

```python
await bot.send_chat_message(message="Hello!", show=True)
# show参数不是必填的，默认为 False ， 即该消息不保存到历史记录中
```

| 参数      | 类型                      | 说明                                              |
| --------- | ------------------------- | ------------------------------------------------- |
| `message` | `str` 或 `MessageSegment` | 要发送的内容                                      |
| `show`    | `bool`                    | 是否保存在聊天记录 (`True` 保存， `False` 不保存) |

#### 返回

空

---

### **2.3 `send_whisper_message(target, message)`**

发送 **私聊消息**：

```python
await bot.send_whisper_message(target="105", message="Hello EFChat!")
```

| 参数      | 类型                      | 说明         |
| --------- | ------------------------- | ------------ |
| `target`  | `str`                     | 目标用户昵称 |
| `message` | `str` 或 `MessageSegment` | 要发送的内容 |

#### 返回

空

---

## **3. 机器人管理**

以下 API 方法用于控制 Bot：

### **3.1 `move(new_channel)`**

移动 Bot 到指定房间：

```python
await bot.move("PrivateRoom")
```

| 参数          | 类型  | 说明         |
| ------------- | ----- | ------------ |
| `new_channel` | `str` | 目标房间名称 |

#### 返回

空，bot 会直接进入新的房间

---

### **3.2 `change_nick(new_nick)`**

修改 Bot 昵称：

```python
await bot.change_nick("EFChatBot")
```

| 参数       | 类型  | 说明     |
| ---------- | ----- | -------- |
| `new_nick` | `str` | 目标昵称 |

#### 返回

空，随后服务器会下发`ChangeNickEvent`事件，父事件为`NoticeEvent`

---

### **3.3 `get_chat_history(num)`**

获取 **历史聊天记录**：

```python
await bot.get_chat_history(num=50)
```

| 参数  | 类型  | 说明             |
| ----- | ----- | ---------------- |
| `num` | `int` | 要获取的消息数量 |

**注意：如果值为`1`，则返回当天的历史聊天记录；如果值为`100`，则返回全部历史聊天记录。**

#### 返回

空，随后服务器会下发`ListHistoryEvent`事件，父事件为`NoticeEvent`

---

## **4. API 调用**

EFChat 适配器支持 **API 调用**，用于执行各种命令：

### **4.1 `call_api(api, **kwargs)`\*\*

调用适配器 API：

```python
await bot.call_api("chat", text="Hello, EFChat!")
```

| 参数     | 类型   | 说明         |
| -------- | ------ | ------------ |
| `api`    | `str`  | API 方法名称 |
| `kwargs` | `dict` | 额外参数     |
