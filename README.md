# Sobry_HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=atomtoto&repository=Sobry_HACS&category=integration)

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

## Installation

### With the button (recommended)

Click the badge above ("Open your Home Assistant instance and open a repository
inside the Home Assistant Community Store"), then **Download**, and restart
Home Assistant.

### Manually (HACS custom repository)

1. In Home Assistant, open **HACS** → **Integrations** → **Custom repositories**
2. Add this repository URL with category **Integration**
3. Install **Sobry Energy**
4. Restart Home Assistant
5. Add **Sobry Energy** from **Settings** → **Devices & Services**

## Brand icon

The integration ships its own brand images in `custom_components/sobry/brand/`
(`icon.png`, `logo.png`). Home Assistant 2026.3 and later loads them directly
from the integration folder, and they take priority over the brands CDN.

On Home Assistant versions older than 2026.3, the frontend only reads icons from
[home-assistant/brands](https://github.com/home-assistant/brands); a custom
integration has no icon there until the images are submitted to that repository
under `custom_integrations/sobry/`.

## Notes

- Without API key, the integration keeps using the existing public endpoint mode.
- Default update interval is 15 minutes.

## Sobry API key (personalized prices)

You can set an optional `api_key` in the integration configuration/options flow.

- When `api_key` is set, the integration uses:
  - `GET https://api.sobry.co/v2/user/daily-prices`
  - Header `Authorization: Bearer <api_key>`
  - No `contractId` query parameter
  - The V2 `date` and `time` response fields (Europe/Paris) to select the
    current and next prices
- When `api_key` is not set, the integration uses the previous endpoint/behavior.

The integration also supports v2 parameters internally:
- `granularity` mapped to `15m` or `1h`
- `taxMode` (`ttc`/`ht`)
