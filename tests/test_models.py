import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from polestar_api.pypolestar.models import (
    CarBatteryData,
    CarInformationData,
    CarOdometerData,
    ChargingConnectionStatus,
    ChargingStatus,
)

DATADIR = Path(__file__).parent.resolve() / "data"

with open(DATADIR / "polestar3.json") as fp:
    POLESTAR_3 = json.load(fp)


def test_car_information_data():
    data = CarInformationData.from_dict(POLESTAR_3["getConsumerCarsV2"])
    # Verify expected attributes
    assert data is not None
    assert isinstance(data, CarInformationData)
    assert data.model_name == "Polestar 3"
    assert data.registration_no == "MLB007"
    assert data.registration_date is None
    assert data.factory_complete_date == date(year=2024, month=4, day=16)


def test_car_information_data_invalid():
    with pytest.raises(KeyError):
        CarInformationData.from_dict({})  # Test with empty dict
    with pytest.raises(TypeError):
        CarInformationData.from_dict(None)  # Test with None


def test_car_battery_data():
    data = CarBatteryData.from_dict(POLESTAR_3["getBatteryData"])
    assert data is not None
    assert isinstance(data, CarBatteryData)
    assert data.average_energy_consumption_kwh_per_100km == 22.4
    assert data.battery_charge_level_percentage == 34
    assert data.charging_status == ChargingStatus.CHARGING_STATUS_IDLE
    assert (
        data.charger_connection_status
        == ChargingConnectionStatus.CHARGER_CONNECTION_STATUS_DISCONNECTED
    )
    assert data.event_updated_timestamp == datetime(
        year=2024,
        month=11,
        day=11,
        hour=17,
        minute=47,
        second=13,
        tzinfo=timezone.utc,
    )
    assert data.event_updated_timestamp.timestamp() == 1731347233


def test_car_battery_data_invalid():
    with pytest.raises(KeyError):
        CarBatteryData.from_dict({})
    with pytest.raises(TypeError):
        CarBatteryData.from_dict(None)


def test_car_odometer_data():
    data = CarOdometerData.from_dict(POLESTAR_3["getOdometerData"])
    assert data is not None
    assert isinstance(data, CarOdometerData)
    assert data.average_speed_km_per_hour == 42.0
    assert data.event_updated_timestamp.timestamp() == 1731338116
    assert data.trip_meter_automatic_km == 4.2


def test_car_odometer_data_invalid():
    with pytest.raises(KeyError):
        CarOdometerData.from_dict({})
    with pytest.raises(TypeError):
        CarOdometerData.from_dict(None)
