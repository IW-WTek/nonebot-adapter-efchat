def sanitize(message: str) -> str:
    """将 `<` 和 `>` 转换为 HTML 实体编码"""
    return message.replace("<", "&lt;").replace(">", "&gt;")
