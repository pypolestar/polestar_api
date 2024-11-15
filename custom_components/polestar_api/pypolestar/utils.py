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

    if field_name is None or not field_name.strip():
        raise ValueError("Field name cannot be empty")

    if data is None:
        return None

    result: GqlScalar | GqlDict = data

    for key in field_name.split("/"):
        if isinstance(result, dict):
            if key not in result:
                raise KeyError(f"Key '{key}' not found in path '{field_name}'")
            result = result[key]
        else:
            raise KeyError(
                f"Cannot access key '{key}' in non-dict value at path '{field_name}'"
            )

    return result


def get_field_name_str(field_name: str, data: GqlDict) -> str | None:
    """Extract a str value from the nested dictionary.
    Args:
        field_name: Path to the str field
        data: Nested dictionary containing the data
    Returns:
        str if successful, None otherwise
    """
    if (value := get_field_name_value(field_name, data)) and (isinstance(value, str)):
        return value


def get_field_name_float(field_name: str, data: GqlDict) -> float | None:
    """Extract a float value from the nested dictionary.
    Args:
        field_name: Path to the float field
        data: Nested dictionary containing the data
    Returns:
        float if successful, None otherwise
    """
    if (value := get_field_name_value(field_name, data)) and isinstance(value, float):
        return value
    elif value is not None:
        try:
            return float(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid float value at '{field_name}': {value}") from exc


def get_field_name_int(field_name: str, data: GqlDict) -> int | None:
    """Extract a int value from the nested dictionary.
    Args:
        field_name: Path to the int field
        data: Nested dictionary containing the data
    Returns:
        int if successful, None otherwise
    """
    if (value := get_field_name_value(field_name, data)) and isinstance(value, int):
        return value
    elif value is not None:
        try:
            return int(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid integer value at '{field_name}': {value}"
            ) from exc


def get_field_name_date(field_name: str, data: GqlDict) -> date | None:
    """Extract and convert a date value from the nested dictionary.
    Args:
        field_name: Path to the date field
        data: Nested dictionary containing the data
    Returns:
        date object if conversion successful, None otherwise
    """
    if value := get_field_name_value(field_name, data):
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid date format at '{field_name}': {value}"
                ) from exc


def get_field_name_datetime(field_name: str, data: GqlDict) -> datetime | None:
    """Extract and convert a datetime value from the nested dictionary.
    Args:
        field_name: Path to the datetime field
        data: Nested dictionary containing the data
    Returns:
        datetime object if conversion successful, None otherwise
    """
    if value := get_field_name_value(field_name, data):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid datetime format at '{field_name}': {value}"
                ) from exc
