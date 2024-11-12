from datetime import date, datetime

GqlScalar = int | float | str | bool | None

GqlDict = dict[str, type["GqlDict"] | GqlScalar]


def get_field_name_value(field_name: str, data: GqlDict) -> GqlScalar | GqlDict:
    if field_name is None or data is None:
        return None

    result: GqlScalar | GqlDict = data
    valid = False

    for key in field_name.split("/"):
        if isinstance(result, dict):
            if key not in result:
                raise KeyError(field_name)
            result = result[key]  # type: ignore
            valid = True
        else:
            raise KeyError(field_name)

    if valid:
        return result

    raise KeyError(field_name)


def get_field_name_str(field_name: str, data: GqlDict) -> str | None:
    if (value := get_field_name_value(field_name, data)) and isinstance(value, str):
        return value


def get_field_name_date(field_name: str, data: GqlDict) -> date | None:
    if (value := get_field_name_value(field_name, data)) and isinstance(value, str):
        return date.fromisoformat(value)


def get_field_name_datetime(field_name: str, data: GqlDict) -> datetime | None:
    if (value := get_field_name_value(field_name, data)) and isinstance(value, str):
        return datetime.fromisoformat(value)
