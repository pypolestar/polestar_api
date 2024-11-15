import json
from pathlib import Path

import pytest
from polestar_api.pypolestar.models import (
    CarBatteryData,
    CarInformationData,
    CarOdometerData,
)

DATADIR = Path(__file__).parent.resolve() / "data"

with open(DATADIR / "polestar3.json") as fp:
    POLESTAR_3 = json.load(fp)


def test_car_information_data():
    data = CarInformationData.from_dict(POLESTAR_3["getConsumerCarsV2"])
    # Verify expected attributes
    assert data is not None
    assert isinstance(data, CarInformationData)
    # Add assertions for expected field values


def test_car_information_data_invalid():
    with pytest.raises(KeyError):
        CarInformationData.from_dict({})  # Test with empty dict
    with pytest.raises(TypeError):
        CarInformationData.from_dict(None)  # Test with None


def test_car_battery_data():
    data = CarBatteryData.from_dict(POLESTAR_3["getBatteryData"])
    assert data is not None
    assert isinstance(data, CarBatteryData)
    # Add assertions for expected field values


def test_car_battery_data_invalid():
    with pytest.raises(KeyError):
        CarBatteryData.from_dict({})
    with pytest.raises(TypeError):
        CarBatteryData.from_dict(None)


def test_car_odometer_data():
    data = CarOdometerData.from_dict(POLESTAR_3["getOdometerData"])
    assert data is not None
    assert isinstance(data, CarOdometerData)
    # Add assertions for expected field values


def test_car_odometer_data_invalid():
    with pytest.raises(KeyError):
        CarOdometerData.from_dict({})
    with pytest.raises(TypeError):
        CarOdometerData.from_dict(None)
