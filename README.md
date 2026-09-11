# Sobry_HA

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=atomtoto&repository=Sobry_HA&category=integration)

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
- Drives appliances directly from the market price, without writing an automation
  (see [Appliance control](#appliance-control)), with a fixed-schedule
  [safety net](#safety-net) when prices cannot be fetched

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


## Appliance control

The integration can decide *when* an appliance should run, and switch it on and
off itself. A water heater set to the 8 cheapest hours of the day no longer
needs a helper entity and an automation.

### Add an appliance

**Settings** → **Devices & Services** → **Sobry Energy** → **Configure** →
**Add an appliance**, then fill in:

| Field | Meaning |
| --- | --- |
| Name | Names the device and its entities, for example `Water heater` |
| Selection mode | How the slots are picked, see below |
| Entity to control | Optional. `switch`, `input_boolean`, `light`, `climate`, `water_heater`, `humidifier` or `fan` |
| Runtime | Hours to schedule per window, for example `8` |
| Extra runtime after the cheap slots | Optional. Keeps running that long after the last selected slot, whatever the price |
| Window start / end | Daily window the slots are picked in. Same start and end means a full day |
| Maximum price | Optional cap: a slot above it is never selected, even if hours are missing |
| Price threshold | Used by the threshold mode |
| Fallback start / end | Optional fixed schedule, used whenever the plan cannot decide. See [Safety net](#safety-net) |
| Wait for the whole window to be priced | Keeps the appliance off until every price of the window is published |

Each appliance becomes its own device. Add as many as you need, and edit or
remove them from the same menu.

### Selection modes

- **Cheapest slots of the window** — the N cheapest slots, consecutive or not.
  This is the classic "8 cheapest hours" behaviour.
- **Cheapest continuous block** — the cheapest single run of N hours, for a
  dishwasher or an EV charge that should not be interrupted.
- **Below a price threshold** — every slot under a price you set.

*Extra runtime* extends the last planned slot by a fixed duration, at whatever
the price is then. It is meant for an appliance whose state you cannot measure:
a water heater with no temperature reading gets its 8 cheap hours plus, say, one
more hour, to be sure it finished heating. The extension applies once per
window, after the last selected slot, and holds even when the price series
stops before its end.

### Entities created per appliance

| Entity | Role |
| --- | --- |
| `binary_sensor.<name>` | `on` while the appliance is scheduled to run. Carries the planned slots, the window, the average planned price and the period in its attributes |
| `sensor.<name>_next_start` | Start of the next planned run |
| `sensor.<name>_next_end` | End of the running window, or of the next one |
| `sensor.<name>_planned_average_price` | Average price of the selected slots |
| `number.<name>_runtime` | Hours to schedule, tunable from a dashboard |
| `number.<name>_price_threshold` | Threshold, for the threshold mode |
| `switch.<name>_automatic_control` | Created when an entity is controlled. Turn it off to take over manually; the appliance is left as it is, and the plan resumes when you turn it back on |
| `binary_sensor.<name>_fixed_schedule_fallback` | Created when a fallback schedule is set. `on` while the fixed schedule is in charge |

The schedule is re-evaluated every minute and on every price refresh, so slots
are honoured to the minute. On restart, the appliance is put back in the state
the plan asks for.

The binary sensor works on its own: leave *Entity to control* empty to keep
driving your appliance from your own automations.

```yaml
automation:
  - alias: Water heater
    triggers:
      - trigger: state
        entity_id: binary_sensor.water_heater
    actions:
      - action: homeassistant.turn_{{ 'on' if trigger.to_state.state == 'on' else 'off' }}
        target:
          entity_id: switch.water_heater_relay
```

### Safety net

An appliance that never runs because a price could not be fetched is worse than
one running at a bad hour. Set a **fallback start** and **fallback end** — your
old off-peak hours, for instance — and the plan switches to that fixed schedule
whenever it cannot decide:

- the Sobry API is unreachable, or answers with an error;
- the prices stop before the current moment (nothing fetched since yesterday);
- the window could not be filled: no price published for it yet, nothing under
  the threshold, or everything above the maximum price.

While the fallback is in charge, `binary_sensor.<name>_fixed_schedule_fallback`
is `on` and the main binary sensor carries `fallback_active: true` along with
the `reason` that caused it — alert on either to know you are flying blind. The
plan takes back over by itself on the next successful refresh.

The safety net also covers a Home Assistant restart while the API is down: as
soon as an appliance is configured, the entities are created even when the first
fetch fails, so the fixed schedule can drive the appliance. A plan with a
runtime of `0` hours is an explicit "do not run" and never triggers the
fallback, and an appliance whose automatic control switch is off is still left
alone.

### `sobry.get_cheapest_slots` service

Returns the cheapest slots of a window without creating an appliance, for
templates, scripts and one-off automations.

```yaml
action: sobry.get_cheapest_slots
data:
  hours: 3
  extra_hours: 1
  window_start: "22:00:00"
  window_end: "06:00:00"
response_variable: cheapest
```

The response holds `slots`, `windows`, `period_start`, `period_end`,
`planned_hours`, `average_price`, `next_start`, `active` and `data_complete`.

### Notes on the price horizon

A plan only selects slots the API has already published. *Wait for the whole
window to be priced* keeps the appliance off until the whole window is known,
so the cheapest slots are never missed by planning on half a day; the
`data_complete` and `reason` attributes of the binary sensor tell you when the
plan is waiting. A window that extends past the published prices — an overnight
window while only today is priced — waits for them: keep the window inside the
day, turn that option off to plan on what is known, or set a fallback schedule
so the appliance runs anyway.

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

## Links
HACS Validation : https://github.com/atomtoto/Sobry_HACS/actions/runs/34109321499/job/101701623660
hassfest Validation : https://github.com/atomtoto/Sobry_HACS/actions/runs/34109321473/job/101701623516
