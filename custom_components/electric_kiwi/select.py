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


HOP_SELECT_TYPE: Final[tuple[ElectricKiwiHOPDescription, ...]] = (
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
    ek_api: ElectricKiwiApi = hass.data[DOMAIN][entry.entry_id]["ek_api"]
    hop_coordinator: ElectricKiwiHOPDataCoordinator = hass.data[DOMAIN][entry.entry_id][
        "hop_coordinator"
    ]

    _LOGGER.debug("Setting up HOP entity")
    entities = [
        ElectricKiwiSelectHOPEntity(
            hop_coordinator, description, ek_api.customer_number, ek_api.connection_id
        )
        for description in HOP_SELECT_TYPE
    ]
    async_add_entities(entities)


class ElectricKiwiSelectHOPEntity(CoordinatorEntity, SelectEntity):
    """Entity object for seeing and setting the hour of free power."""

    entity_description: ElectricKiwiHOPDescription
    values_dict: dict[str, int]

    def __init__(
        self,
        hop_coordinator: ElectricKiwiHOPDataCoordinator,
        description: ElectricKiwiHOPDescription,
        customer_number: int,
        connection_id: int,
    ) -> None:
        """Initialise the HOP selection entity."""
        super().__init__(hop_coordinator)
        self._hop_coordinator: ElectricKiwiHOPDataCoordinator = hop_coordinator
        self.entity_description = description
        self._state = None
        self.customer_number = customer_number
        self.connection_id = connection_id
        self.values_dict = self._hop_coordinator.get_hop_options()
        self._attr_options = list(self.values_dict.keys())
        self._async_update_attrs()

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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        self._async_update_attrs()
        super()._handle_coordinator_update()

    def _get_current_option(self) -> str | None:
        return f"{self._hop_coordinator.get_selected_hop().start.start_time} - {self._hop_coordinator.get_selected_hop().end.end_time}"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self.values_dict[option]
        await self._hop_coordinator.async_update_hop(value)
        self._attr_current_option = option
        self.async_write_ha_state()

    @callback
    def _async_update_attrs(self) -> None:
        """Update select attributes."""
        self._attr_current_option = self._get_current_option()
        _LOGGER.debug("Hop data from coordinator: %s", self._hop_coordinator.data)
