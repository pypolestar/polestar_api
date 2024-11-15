from datetime import date, datetime

GqlScalar = int | float | str | bool | None

GqlDict = dict[str, type["GqlDict"] | GqlScalar]


def get_field_name_value(field_name: str, data: GqlDict) -> GqlScalar | GqlDict:
    """Extract a value from nested dictionary using path-like notation.
    
    Args:
        field_name: Path to the field using "/" as separator (e.g., "car/status/battery")
        data: Nested dictionary containing the data
        
    Returns:
        The value at the specified path
        
    Raises:
        KeyError: If the path doesn't exist or is invalid
    """
    if field_name is None or data is None:
        return None

    result: GqlScalar | GqlDict = data

    for key in field_name.split("/"):
        if isinstance(result, dict):
            if key not in result:
                raise KeyError(f"Key '{key}' not found in path '{field_name}'")
            result = result[key]
        else:
            raise KeyError(f"Cannot access key '{key}' in non-dict value at path '{field_name}'")

    return result

def get_field_name_str(field_name: str, data: GqlDict) -> str | None:
    if (value := get_field_name_value(field_name, data)) and isinstance(value, str):
        return value


def get_field_name_float(field_name: str, data: GqlDict) -> float | None:
    if (value := get_field_name_value(field_name, data)) and isinstance(value, float):
        return value


def get_field_name_int(field_name: str, data: GqlDict) -> int | None:
    if (value := get_field_name_value(field_name, data)) and isinstance(value, int):
        return value


def get_field_name_date(field_name: str, data: GqlDict) -> date | None:
    if (value := get_field_name_value(field_name, data)) and isinstance(value, str):
        return date.fromisoformat(value)


def get_field_name_datetime(field_name: str, data: GqlDict) -> datetime | None:
    if (value := get_field_name_value(field_name, data)) and isinstance(value, str):
        return datetime.fromisoformat(value)
