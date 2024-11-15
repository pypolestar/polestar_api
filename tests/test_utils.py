from datetime import date, datetime

import pytest
from polestar_api.pypolestar.utils import (
    get_field_name_date,
    get_field_name_datetime,
    get_field_name_float,
    get_field_name_int,
    get_field_name_str,
    get_field_name_value,
)

TESTDATA = {
    "vin": "YSMYKEAE7RB000000",
    "internalVehicleIdentifier": "0c5f757e-5eb3-4191-b786-0513ddaa452f",
    "registrationNo": "MLB007",
    "registrationDate": None,
    "factoryCompleteDate": "2024-04-16",
    "content": {
        "model": {"name": "Polestar 3"},
        "images": {
            "studio": {"url": "https://example.com/image.png"},
            "specification": {
                "battery": "400V lithium-ion battery, 111 kWh capacity, 17 modules",
                "torque": "840 Nm / 620 lbf-ft",
            },
        },
        "software": {"version": None, "versionTimestamp": None},
    },
    "averageEnergyConsumptionKwhPer100Km": 42.01,
    "batteryChargeLevelPercentage": 100,
}


def test_get_field_name_value():
    assert get_field_name_value("vin", TESTDATA) == "YSMYKEAE7RB000000"
    assert get_field_name_value("content/model/name", TESTDATA) == "Polestar 3"
    assert get_field_name_value("content/software/version", TESTDATA) is None
    assert get_field_name_value("content/images/studio", TESTDATA) == {
        "url": "https://example.com/image.png"
    }
    with pytest.raises(KeyError):
        assert (
            get_field_name_value("content/model/name/xyzzy", TESTDATA) == "Polestar 3"
        )
    with pytest.raises(KeyError):
        get_field_name_value("xyzzy", TESTDATA)
    with pytest.raises(KeyError):
        get_field_name_value("content/xyzzy", TESTDATA)


def test_get_field_name_str():
    assert get_field_name_str("vin", TESTDATA) == "YSMYKEAE7RB000000"
    assert get_field_name_str("registrationDate", TESTDATA) is None  # None handling


def test_get_field_name_float():
    assert (
        get_field_name_float("averageEnergyConsumptionKwhPer100Km", TESTDATA) == 42.01
    )
    assert get_field_name_float("registrationDate", TESTDATA) is None  # None handling


def test_get_field_name_int():
    assert get_field_name_int("batteryChargeLevelPercentage", TESTDATA) == 100
    assert get_field_name_int("registrationDate", TESTDATA) is None  # None handling


def test_get_field_name_date():
    assert get_field_name_date("factoryCompleteDate", TESTDATA) == date(2024, 4, 16)
    assert get_field_name_date("registrationDate", TESTDATA) is None  # None handling
    with pytest.raises(ValueError):  # Invalid date
        get_field_name_date("vin", TESTDATA)


def test_get_field_name_datetime():
    assert get_field_name_datetime("factoryCompleteDate", TESTDATA) == datetime(
        2024, 4, 16
    )
    assert (
        get_field_name_datetime("registrationDate", TESTDATA) is None
    )  # None handling
    with pytest.raises(ValueError):  # Invalid datetime
        get_field_name_datetime("vin", TESTDATA)
