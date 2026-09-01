# Sobry_HACS

Sobry Energy integration for Home Assistant Community Store (HACS), based on the Sobry V2 API.

## Features

- Pulls electricity prices from `https://api.sobry.co/api/prices/raw`
- Supports Sobry pricing options (`segment`, `turpe`, `profil`, `display`)
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

- Uses Sobry public V2 price endpoint and does not require API credentials.
- Default update interval is 15 minutes.
