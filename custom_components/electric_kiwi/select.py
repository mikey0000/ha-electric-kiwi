"""Support for Electric Kiwi hour of free power."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Final

from electrickiwi_api import ElectricKiwiApi

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_EK_HOP_SELECT, DOMAIN, ATTRIBUTION
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


HOP_SELECT_TYPES: Final[ElectricKiwiHOPDescription, ...] = (
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
        for description in HOP_SELECT_TYPES
    ]
    async_add_entities(entities)


class ElectricKiwiSelectHOPEntity(
    CoordinatorEntity[ElectricKiwiHOPDataCoordinator], SelectEntity
):
    """Entity object for seeing and setting the hour of free power."""

    entity_description: SelectEntityDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    values_dict: dict[str, int]

    def __init__(
        self,
        coordinator: ElectricKiwiHOPDataCoordinator,
        description: SelectEntityDescription,
    ) -> None:
        """Initialise the HOP selection entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator._ek_api.customer_number}\
            _{coordinator._ek_api.connection_id}_{description.key}"
        self.entity_description = description
        self.values_dict = coordinator.get_hop_options()
        self._attr_options = list(self.values_dict)

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        return  (
            f'{self.coordinator.data.start.start_time}'
            f' - {self.coordinator.data.end.end_time}'
            )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self.values_dict[option]
        await self.coordinator.async_update_hop(value)
        self.async_write_ha_state()
