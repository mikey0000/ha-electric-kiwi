"""Support for Electric Kiwi hour of free power."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Final

from electrickiwi_api import ElectricKiwiApi

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_EK_HOP_SELECT, DOMAIN
from .coordinator import ElectricKiwiHOPDataCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class ElectricKiwiHOPSelectDescriptionMixin:
    """Define an entity description mixin for select entities."""

    options_dict: dict[str, int] | None


@dataclass
class ElectricKiwiHOPDescription(
    SelectEntityDescription, ElectricKiwiHOPSelectDescriptionMixin
):
    """Class to describe an Electric Kiwi select entity."""


HOP_SELECT_TYPE: Final[ElectricKiwiHOPDescription, ...] = (
    ElectricKiwiHOPDescription(
        entity_category=EntityCategory.CONFIG,
        key=ATTR_EK_HOP_SELECT,
        name="Hour of free power",
        options_dict=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Electric Kiwi Sensor Setup."""
    hop_coordinator: ElectricKiwiHOPDataCoordinator = hass.data[DOMAIN][entry.entry_id][
        "hop_coordinator"
    ]

    _LOGGER.debug("Setting up HOP entity")
    entities = [
        ElectricKiwiSelectHOPEntity(
            hop_coordinator, description
        )
        for description in HOP_SELECT_TYPE
    ]
    async_add_entities(entities)


class ElectricKiwiSelectHOPEntity(CoordinatorEntity[ElectricKiwiHOPDataCoordinator], SelectEntity):
    """Entity object for seeing and setting the hour of free power."""

    entity_description: ElectricKiwiHOPDescription
    values_dict: dict[str, int]

    def __init__(
        self,
        hop_coordinator: ElectricKiwiHOPDataCoordinator,
        description: ElectricKiwiHOPDescription,
    ) -> None:
        """Initialise the HOP selection entity."""
        super().__init__(hop_coordinator)
        self.entity_description = description
        self._state = None
        self.customer_number = self.coordinator._ek_api.customer_number
        self.connection_id = self.coordinator._ek_api.connection_id
        self.values_dict = self.coordinator.get_hop_options()
        self._attr_options = list(self.values_dict.keys())

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.customer_number}_{str(self.connection_id)}\
            _{self.entity_description.key}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        super()._handle_coordinator_update()

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        return f"{self.coordinator.data.start.start_time}\
            - {self.coordinator.data.end.end_time}"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self.values_dict[option]
        await self.coordinator.async_update_hop(value)
        self.async_write_ha_state()