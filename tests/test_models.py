import json
import os
from pathlib import Path

from polestar_api.pypolestar.models import (
    CarBatteryData,
    CarInformationData,
    CarOdometerData,
)

DATADIR = Path(os.path.abspath(os.path.dirname(__file__))) / "data"

with open(DATADIR / "polestar3.json") as fp:
    POLESTAR_3 = json.load(fp)


def test_car_information_data():
    _ = CarInformationData.from_dict(POLESTAR_3["getConsumerCarsV2"])


def test_car_battery_data():
    _ = CarBatteryData.from_dict(POLESTAR_3["getBatteryData"])


def test_car_odometer_data():
    _ = CarOdometerData.from_dict(POLESTAR_3["getOdometerData"])
