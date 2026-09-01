# Sobry_HACS

Sobry Energy integration for Home Assistant Community Store (HACS), based on the Sobry V2 API.

## Features

- Pulls electricity prices from `https://api.sobry.co/api/prices/raw`
- Supports Sobry pricing options (`segment`, `turpe`, `profil`, `display`)
- Supports Sobry API key mode for personalized prices (`/v2/user/daily-prices`)
- Creates Home Assistant sensors for:
  - Current price
  - Next price
  - Minimum price
  - Maximum price
  - Average price
- Exposes full returned price list in `all_prices` attribute of the current price sensor

## Installation (HACS custom repository)

1. In Home Assistant, open **HACS** → **Integrations** → **Custom repositories**
2. Add this repository URL with category **Integration**
3. Install **Sobry Energy**
4. Restart Home Assistant
5. Add **Sobry Energy** from **Settings** → **Devices & Services**

## Notes

- Without API key, the integration keeps using the existing public endpoint mode.
- Default update interval is 15 minutes.

## Sobry API key (personalized prices)

You can set an optional `api_key` in the integration configuration/options flow.

- When `api_key` is set, the integration uses:
  - `GET https://api.sobry.co/v2/user/daily-prices`
  - Header `Authorization` with a ****** key
  - No `contractId` query parameter
- When `api_key` is not set, the integration uses the previous endpoint/behavior.

The integration also supports v2 parameters internally:
- `granularity` mapped to `15m` or `1h`
- `taxMode` (`ttc`/`ht`)
