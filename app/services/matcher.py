def matches_keyword(keyword: str, text: str) -> bool:
    if not keyword or not text:
        return False
    return keyword.lower().strip() in text.lower()
