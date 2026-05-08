from __future__ import annotations


def require_value(data: dict, key: str) -> str:
    value = data.get(key)
    if value is None:
        raise ValueError("{0} is required".format(key))
    if isinstance(value, str):
        value = value.strip()
    if value == "":
        raise ValueError("{0} is required".format(key))
    return value


def listify(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()]


def optional_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return float(value)


def optional_int(value, *, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    return int(value)
