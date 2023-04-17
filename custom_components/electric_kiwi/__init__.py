"""The Electric Kiwi integration."""
from __future__ import annotations

import aiohttp
from electrickiwi_api import ElectricKiwiApi
from electrickiwi_api.exceptions import AuthException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow

from . import api
from .const import DOMAIN
from .coordinator import (
    ElectricKiwiAccountDataCoordinator,
    ElectricKiwiHOPDataCoordinator,
)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Electric Kiwi from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed(err) from err
        raise ConfigEntryNotReady from err
    except aiohttp.ClientError as err:
        raise ConfigEntryNotReady from err

    ek_api = ElectricKiwiApi(
        api.AsyncConfigEntryAuth(aiohttp_client.async_get_clientsession(hass), session)
    )
    account_coordinator = ElectricKiwiAccountDataCoordinator(hass, ek_api)
    hop_coordinator = ElectricKiwiHOPDataCoordinator(hass, ek_api)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "ek_api": ek_api,
        "account_coordinator": account_coordinator,
        "hop_coordinator": hop_coordinator,
    }

    # we need to set the client number and connection id
    try:
        await hass.data[DOMAIN][entry.entry_id]["ek_api"].set_active_session()
        await hop_coordinator.async_config_entry_first_refresh()
        await account_coordinator.async_config_entry_first_refresh()
    except AuthException as err:
        raise ConfigEntryAuthFailed(err) from err

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
