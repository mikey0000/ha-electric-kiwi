"""Support for Electric Kiwi account balance."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging

from electrickiwi_api.model import AccountBalance

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
    ATTR_EK_HOP,
    ATTR_HOP_PERCENTAGE,
    ATTR_NEXT_BILLING_DATE,
    ATTR_TOTAL_CURRENT_BALANCE,
    ATTR_TOTAL_RUNNING_BALANCE,
    ATTRIBUTION,
    DOMAIN,
    NAME,
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
        name=f"{NAME} total running balance",
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_DOLLAR,
        value_func=lambda account_balance: account_balance.total_running_balance,
    ),
    ElectricKiwiSensorEntityDescription(
        key=ATTR_TOTAL_CURRENT_BALANCE,
        name=f"{NAME} total current balance",
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_DOLLAR,
        value_func=lambda account_balance: account_balance.total_account_balance,
    ),
    ElectricKiwiSensorEntityDescription(
        key=ATTR_NEXT_BILLING_DATE,
        name=f"{NAME} next billing date",
        icon="mdi:calendar",
        device_class=SensorDeviceClass.DATE,
        value_func=lambda account_balance: datetime.strptime(
            account_balance.next_billing_date, "%Y-%m-%d"
        ),
    ),
    ElectricKiwiSensorEntityDescription(
        key=ATTR_HOP_PERCENTAGE,
        name=f"{NAME} Hour of Power savings",
        icon="",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_func=lambda account_balance: account_balance.connections[
            0
        ].hop_percentage,
    ),
)

HOP_SENSOR_TYPE: tuple[ElectricKiwiSensorEntityDescription, ...] = (
    ElectricKiwiSensorEntityDescription(
        key=ATTR_EK_HOP,
        name=f"{NAME} Hour of free power",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_func=lambda hop_start_time: datetime.combine(
            datetime.today(), datetime.strptime(hop_start_time, "%I:%M %p").time()
        ).astimezone(dt_util.DEFAULT_TIME_ZONE),
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
        ElectricKiwiAccountEntity(account_coordinator, description)
        for description in ACCOUNT_SENSOR_TYPES
    ]
    async_add_entities(entities)

    hop_coordinator: ElectricKiwiHOPDataCoordinator = hass.data[DOMAIN][entry.entry_id][
        "hop_coordinator"
    ]

    hop_entities = [
        ElectricKiwiHOPEntity(hop_coordinator, description)
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
    ) -> None:
        """Entity object for Electric Kiwi sensor."""
        super().__init__(account_coordinator)
        self._account_coordinator: ElectricKiwiAccountDataCoordinator = (
            account_coordinator
        )

        self._balance: AccountBalance
        self.entity_description = description
        self._attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._account_coordinator.customer_number}_{self._account_coordinator.connection_id}_{self.entity_description.key}"

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

    entity_description: ElectricKiwiSensorEntityDescription

    def __init__(
        self,
        hop_coordinator: ElectricKiwiHOPDataCoordinator,
        description: ElectricKiwiSensorEntityDescription,
    ) -> None:
        """Entity object for Electric Kiwi sensor."""
        super().__init__(hop_coordinator)
        self._hop_coordinator: ElectricKiwiHOPDataCoordinator = hop_coordinator
        self.entity_description = description

        self._balance: AccountBalance
        self.entity_description = description
        self._attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._hop_coordinator.customer_number}_{self._hop_coordinator.connection_id}_{self.entity_description.name}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.entity_description.name}"

    @property
    def native_value(self) -> datetime | str | None:
        """Return the state of the sensor."""
        return self.entity_description.value_func(
            self._hop_coordinator.get_selected_hop().start.start_time
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return self._attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        self._attr_native_value = self.entity_description.value_func(
            self._hop_coordinator.get_selected_hop().start.start_time
        )
        super()._handle_coordinator_update()

    async def async_update(self) -> None:
        """Get the latest data from Electric Kiwi and updates the HOP."""
        await super().async_update()
        logging.debug("HOP data from sensor: %s", self._hop_coordinator.data)
