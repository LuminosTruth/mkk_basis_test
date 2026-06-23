def enum_values(enum_cls: type) -> list[str]:
    return [item.value for item in enum_cls]
