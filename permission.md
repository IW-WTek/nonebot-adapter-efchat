## 权限说明

- `ChannelMessageEvent`事件中的`role`字段，即为`level`字段值所对应的角色

### 权限对照表 (由高到低)
| level | role             | 说明                                 |
| ----- | ---------------- | ------------------------------------ |
| 55105 | admin            | 站长                                 |
| 25555 | moderator        | 管理员                               |
| 10555 | channelOwner     | 房主（非公屏可踢人）                 |
| 15555 | channelModerator | 房间管理员（暂时没用）               |
| 82200 | Yana             | 服务器机娘                           |
| 5155  | channelTrusted   | 房间信任（锁房用的没用）             |
| 1055  | trustedUser      | 信任用户（可以跳过房间锁定和验证码） |
| 105   | default          | 默认用户                             |
