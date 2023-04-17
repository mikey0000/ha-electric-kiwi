"""Electric Kiwi coordinators."""
from datetime import timedelta
import logging

import async_timeout
from electrickiwi_api import ElectricKiwiApi
from electrickiwi_api.exceptions import ApiException, AuthException
from electrickiwi_api.model import AccountBalance, Hop, HopIntervals

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

ACCOUNT_SCAN_INTERVAL = timedelta(hours=6)
HOP_SCAN_INTERVAL = timedelta(hours=2)


class ElectricKiwiAccountDataCoordinator(DataUpdateCoordinator):
    """ElectricKiwi Data object."""

    def __init__(self, hass: HomeAssistant, ek_api: ElectricKiwiApi) -> None:
        """Initialize ElectricKiwiAccountDataCoordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Electric Kiwi Account Data",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=ACCOUNT_SCAN_INTERVAL,
        )
        self._ek_api = ek_api
        self.customer_number = ek_api.customer_number
        self.connection_id = ek_api.connection_id

    async def _async_update_data(self) -> AccountBalance:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(60):
                return await self._ek_api.get_account_balance()
        except AuthException as auth_err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from auth_err
        except ApiException as api_err:
            raise UpdateFailed(
                f"Error communicating with EK API: {api_err}"
            ) from api_err


class ElectricKiwiHOPDataCoordinator(DataUpdateCoordinator):
    """ElectricKiwi Data object."""

    def __init__(self, hass: HomeAssistant, ek_api: ElectricKiwiApi) -> None:
        """Initialize ElectricKiwiAccountDataCoordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Electric Kiwi HOP Data",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=HOP_SCAN_INTERVAL,
        )
        self._ek_api = ek_api
        self.customer_number = ek_api.customer_number
        self.connection_id = ek_api.connection_id
        self.hop_intervals: HopIntervals = None

    def get_hop_options(self) -> dict[str, int]:
        """Get the hop interval options for selection."""
        return {
            f"{v.start_time} - {v.end_time}": k
            for k, v in self.hop_intervals.intervals.items()
        }

    def get_selected_hop(self) -> Hop:
        """Get currently selected hop."""
        return self.data

    async def async_update_hop(self, hop_interval: int) -> Hop:
        """Update selected hop and data."""
        self.data = await self._ek_api.post_hop(hop_interval)
        self.async_update_listeners()
        return self.data

    async def _async_update_data(self) -> Hop:
        """Fetch data from API endpoint.

        filters the intervals to remove ones that are not active
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(60):
                if self.hop_intervals is None:
                    hop_intervals: HopIntervals = await self._ek_api.get_hop_intervals()
                    hop_intervals.intervals = dict(
                        filter(
                            lambda pair: pair[1].active == 1,
                            hop_intervals.intervals.items(),
                        )
                    )

                    self.hop_intervals = hop_intervals
                return await self._ek_api.get_hop()
        except AuthException as auth_err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from auth_err
        except ApiException as api_err:
            raise UpdateFailed(
                f"Error communicating with EK API: {api_err}"
            ) from api_err
