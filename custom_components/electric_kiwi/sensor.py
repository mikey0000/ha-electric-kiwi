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


HOP_SENSOR_TYPE: tuple[ElectricKiwiHOPSensorEntityDescription, ...] = (
    ElectricKiwiHOPSensorEntityDescription(
        key=ATTR_EK_HOP_START,
        name="Hour of free power start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_func=lambda hop: datetime.combine(
            datetime.today(), datetime.strptime(hop.start.start_time, "%I:%M %p").time()
        ).astimezone(dt_util.DEFAULT_TIME_ZONE),
    ),
    ElectricKiwiHOPSensorEntityDescription(
        key=ATTR_EK_HOP_END,
        name="Hour of free power end",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_func=lambda hop: datetime.combine(
            datetime.today(),
            datetime.strptime(hop.end.end_time, "%I:%M %p").time(),
        ).astimezone(dt_util.DEFAULT_TIME_ZONE),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Electric Kiwi Sensor Setup."""
    ek_api: ElectricKiwiApi = hass.data[DOMAIN][entry.entry_id]["ek_api"]
    account_coordinator: ElectricKiwiAccountDataCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]["account_coordinator"]

    entities = [
        ElectricKiwiAccountEntity(
            account_coordinator,
            description,
            ek_api.customer_number,
            ek_api.connection_id,
        )
        for description in ACCOUNT_SENSOR_TYPES
    ]
    async_add_entities(entities)

    hop_coordinator: ElectricKiwiHOPDataCoordinator = hass.data[DOMAIN][entry.entry_id][
        "hop_coordinator"
    ]

    hop_entities = [
        ElectricKiwiHOPEntity(
            hop_coordinator, description, ek_api.customer_number, ek_api.connection_id
        )
        for description in HOP_SENSOR_TYPE
    ]
    async_add_entities(hop_entities)


class ElectricKiwiAccountEntity(CoordinatorEntity, SensorEntity):
    """Entity object for Electric Kiwi sensor."""

    entity_description: ElectricKiwiSensorEntityDescription

    def __init__(
        self,
        account_coordinator: ElectricKiwiAccountDataCoordinator,
        description: ElectricKiwiSensorEntityDescription,
        customer_number: int,
        connection_id: int,
    ) -> None:
        """Entity object for Electric Kiwi sensor."""
        super().__init__(account_coordinator)
        self._account_coordinator: ElectricKiwiAccountDataCoordinator = (
            account_coordinator
        )
        self.customer_number = customer_number
        self.connection_id = connection_id
        self._balance: AccountBalance
        self.entity_description = description
        self._attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return "_".join(
            [
                str(self.customer_number),
                str(self.connection_id),
                self.entity_description.key,
            ]
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.entity_description.name}"

    @property
    def native_value(self) -> datetime | str | None:
        """Return the state of the sensor."""
        return self.entity_description.value_func(self._account_coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return self._attributes

    async def async_update(self) -> None:
        """Get the latest data from Electric Kiwi and updates the balances."""
        await super().async_update()
        logging.debug("Account data from sensor: %s", self._account_coordinator.data)


class ElectricKiwiHOPEntity(CoordinatorEntity, SensorEntity):
    """Entity object for Electric Kiwi sensor."""

    entity_description: ElectricKiwiHOPSensorEntityDescription

    def __init__(
        self,
        hop_coordinator: ElectricKiwiHOPDataCoordinator,
        description: ElectricKiwiHOPSensorEntityDescription,
        customer_number: int,
        connection_id: int,
    ) -> None:
        """Entity object for Electric Kiwi sensor."""
        super().__init__(hop_coordinator)
        self._hop_coordinator: ElectricKiwiHOPDataCoordinator = hop_coordinator
        self.entity_description = description

        self.customer_number = customer_number
        self.connection_id = connection_id
        self.entity_description = description
        self._attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return "_".join(
            [
                str(self.customer_number),
                str(self.connection_id),
                self.entity_description.key,
            ]
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.entity_description.name}"

    @property
    def native_value(self) -> datetime | str | None:
        """Return the state of the sensor."""
        value: datetime = self.entity_description.value_func(
            self._hop_coordinator.get_selected_hop()
        )

        end_time = datetime.combine(
            datetime.today(),
            datetime.strptime(
                self._hop_coordinator.get_selected_hop().end.end_time, "%I:%M %p"
            ).time(),
        ).astimezone(dt_util.DEFAULT_TIME_ZONE)

        if end_time < datetime.now().astimezone(dt_util.DEFAULT_TIME_ZONE):
            return value + timedelta(days=1)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return self._attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        self._attr_native_value = self.entity_description.value_func(
            self._hop_coordinator.get_selected_hop()
        )
        super()._handle_coordinator_update()

    async def async_update(self) -> None:
        """Get the latest data from Electric Kiwi and updates the HOP."""
        await super().async_update()
        logging.debug("HOP data from sensor: %s", self._hop_coordinator.data)
