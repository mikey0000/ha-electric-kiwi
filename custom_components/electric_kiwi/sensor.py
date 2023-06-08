"""Support for Electric Kiwi account balance."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from electrickiwi_api import ElectricKiwiApi
from electrickiwi_api.model import AccountBalance, Hop

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CURRENCY_DOLLAR, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_EK_HOP_END,
    ATTR_EK_HOP_START,
    ATTR_HOP_PERCENTAGE,
    ATTR_NEXT_BILLING_DATE,
    ATTR_TOTAL_CURRENT_BALANCE,
    ATTR_TOTAL_RUNNING_BALANCE,
    ATTRIBUTION,
    DOMAIN,
)
from .coordinator import (
    ElectricKiwiAccountDataCoordinator,
    ElectricKiwiHOPDataCoordinator,
)


@dataclass
class ElectricKiwiRequiredKeysMixin:
    """Mixin for required keys."""

    value_func: Callable[[AccountBalance], str | datetime | None]


@dataclass
class ElectricKiwiSensorEntityDescription(
    SensorEntityDescription, ElectricKiwiRequiredKeysMixin
):
    """Describes Electric Kiwi sensor entity."""


ACCOUNT_SENSOR_TYPES: tuple[ElectricKiwiSensorEntityDescription, ...] = (
    ElectricKiwiSensorEntityDescription(
        key=ATTR_TOTAL_RUNNING_BALANCE,
        name="Total running balance",
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_DOLLAR,
        value_func=lambda account_balance: str(account_balance.total_running_balance),
    ),
    ElectricKiwiSensorEntityDescription(
        key=ATTR_TOTAL_CURRENT_BALANCE,
        name="Total current balance",
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_DOLLAR,
        value_func=lambda account_balance: str(account_balance.total_account_balance),
    ),
    ElectricKiwiSensorEntityDescription(
        key=ATTR_NEXT_BILLING_DATE,
        name="Next billing date",
        icon="mdi:calendar",
        device_class=SensorDeviceClass.DATE,
        value_func=lambda account_balance: datetime.strptime(
            account_balance.next_billing_date, "%Y-%m-%d"
        ),
    ),
    ElectricKiwiSensorEntityDescription(
        key=ATTR_HOP_PERCENTAGE,
        name="Hour of power savings",
        icon="",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_func=lambda account_balance: str(
            account_balance.connections[0].hop_percentage
        ),
    ),
)


@dataclass
class ElectricKiwiHOPRequiredKeysMixin:
    """Mixin for required HOP keys."""

    value_func: Callable[[Hop], datetime]


@dataclass
class ElectricKiwiHOPSensorEntityDescription(
    SensorEntityDescription,
    ElectricKiwiHOPRequiredKeysMixin,
):
    """Describes Electric Kiwi HOP sensor entity."""


def check_and_move_time(time: datetime, hop: Hop):
    """moves time forward by a day if HOP is in the past"""
    end_time = datetime.combine(
        datetime.today(),
        datetime.strptime(hop.end.end_time, "%I:%M %p").time(),
    ).astimezone(dt_util.DEFAULT_TIME_ZONE)

    if end_time < datetime.now().astimezone(dt_util.DEFAULT_TIME_ZONE):
        return time + timedelta(days=1)
    return time


HOP_SENSOR_TYPE: tuple[ElectricKiwiHOPSensorEntityDescription, ...] = (
    ElectricKiwiHOPSensorEntityDescription(
        key=ATTR_EK_HOP_START,
        name="Hour of free power start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_func=lambda hop: check_and_move_time(
            datetime.combine(
                datetime.today(),
                datetime.strptime(hop.start.start_time, "%I:%M %p").time(),
            ).astimezone(dt_util.DEFAULT_TIME_ZONE),
            hop,
        ),
    ),
    ElectricKiwiHOPSensorEntityDescription(
        key=ATTR_EK_HOP_END,
        name="Hour of free power end",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_func=lambda hop: check_and_move_time(
            datetime.combine(
                datetime.today(),
                datetime.strptime(hop.end.end_time, "%I:%M %p").time(),
            ).astimezone(dt_util.DEFAULT_TIME_ZONE),
            hop,
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Electric Kiwi Sensor Setup."""
    account_coordinator: ElectricKiwiAccountDataCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]["account_coordinator"]

    entities = [
        ElectricKiwiAccountEntity(
            account_coordinator,
            description,
        )
        for description in ACCOUNT_SENSOR_TYPES
    ]
    async_add_entities(entities)

    hop_coordinator: ElectricKiwiHOPDataCoordinator = hass.data[DOMAIN][entry.entry_id][
        "hop_coordinator"
    ]

    hop_entities = [
        ElectricKiwiHOPEntity(
            hop_coordinator,
            description,
        )
        for description in HOP_SENSOR_TYPE
    ]
    async_add_entities(hop_entities)


class ElectricKiwiAccountEntity(
    CoordinatorEntity[ElectricKiwiAccountDataCoordinator], SensorEntity
):
    """Entity object for Electric Kiwi sensor."""

    entity_description: ElectricKiwiSensorEntityDescription
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        account_coordinator: ElectricKiwiAccountDataCoordinator,
        description: ElectricKiwiSensorEntityDescription,
    ) -> None:
        """Entity object for Electric Kiwi sensor."""
        super().__init__(account_coordinator)

        self.customer_number = self.coordinator._ek_api.customer_number
        self.connection_id = self.coordinator._ek_api.connection_id
        self._balance: AccountBalance
        self.entity_description = description

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.customer_number}_{str(self.connection_id)}_{self.entity_description.key}"

    @property
    def native_value(self) -> datetime | str | None:
        """Return the state of the sensor."""
        return self.entity_description.value_func(self.coordinator.data)


class ElectricKiwiHOPEntity(
    CoordinatorEntity[ElectricKiwiHOPDataCoordinator], SensorEntity
):
    """Entity object for Electric Kiwi sensor."""

    entity_description: ElectricKiwiHOPSensorEntityDescription
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        hop_coordinator: ElectricKiwiHOPDataCoordinator,
        description: ElectricKiwiHOPSensorEntityDescription,
    ) -> None:
        """Entity object for Electric Kiwi sensor."""
        super().__init__(hop_coordinator)

        self.customer_number = self.coordinator._ek_api.customer_number
        self.connection_id = self.coordinator._ek_api.connection_id
        self.entity_description = description

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.customer_number}_{str(self.connection_id)}_{self.entity_description.key}"

    @property
    def native_value(self) -> datetime:
        """Return the state of the sensor."""
        return self.entity_description.value_func(self.coordinator.data)
