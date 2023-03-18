"""Support for Electric Kiwi account balance."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging

from electrickiwi_api import ElectricKiwiApi
from electrickiwi_api.model import AccountBalance

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CURRENCY_DOLLAR, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_HOP_PERCENTAGE,
    ATTR_NEXT_BILLING_DATE,
    ATTR_TOTAL_CURRENT_BALANCE,
    ATTR_TOTAL_RUNNING_BALANCE,
    ATTRIBUTION,
    DOMAIN,
    NAME,
)
from .coordinator import ElectricKiwiAccountDataCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class ElectricKiwiAccountRequiredKeysMixin:
    """Mixin for required keys."""

    value_func: Callable[[AccountBalance], str | datetime | None]


@dataclass
class ElectricKiwiAccountSensorEntityDescription(
    SensorEntityDescription, ElectricKiwiAccountRequiredKeysMixin
):
    """Describes Electric Kiwi sensor entity."""


ACCOUNT_SENSOR_TYPES: tuple[ElectricKiwiAccountSensorEntityDescription, ...] = (
    ElectricKiwiAccountSensorEntityDescription(
        key=ATTR_TOTAL_RUNNING_BALANCE,
        name=f"{NAME} total running balance",
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_DOLLAR,
        value_func=lambda account_balance: account_balance.total_running_balance,
    ),
    ElectricKiwiAccountSensorEntityDescription(
        key=ATTR_TOTAL_CURRENT_BALANCE,
        name=f"{NAME} total current balance",
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_DOLLAR,
        value_func=lambda account_balance: account_balance.total_account_balance,
    ),
    ElectricKiwiAccountSensorEntityDescription(
        key=ATTR_NEXT_BILLING_DATE,
        name=f"{NAME} next billing date",
        icon="mdi:calendar",
        device_class=SensorDeviceClass.DATE,
        value_func=lambda account_balance: datetime.strptime(
            account_balance.next_billing_date, "%Y-%m-%d"
        ),
    ),
    ElectricKiwiAccountSensorEntityDescription(
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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Electric Kiwi Sensor Setup."""
    ek_api: ElectricKiwiApi = hass.data[DOMAIN][entry.entry_id]
    account_coordinator = ElectricKiwiAccountDataCoordinator(hass, ek_api)
    await account_coordinator.async_config_entry_first_refresh()

    entities = [
        ElectricKiwiAccountEntity(account_coordinator, description)
        for description in ACCOUNT_SENSOR_TYPES
    ]
    async_add_entities(entities)


class ElectricKiwiAccountEntity(CoordinatorEntity, SensorEntity):
    """Entity object for Electric Kiwi sensor."""

    entity_description: ElectricKiwiAccountSensorEntityDescription

    def __init__(
        self,
        account_coordinator: ElectricKiwiAccountDataCoordinator,
        description: ElectricKiwiAccountSensorEntityDescription,
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
        _LOGGER.debug("Account data from sensor: %s", self._account_coordinator.data)
