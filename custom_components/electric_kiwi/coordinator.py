



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