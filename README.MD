> 2024-10-08
> 
> Dear Peaquser,
> 
> After three years of open source in these projects, I am about to set sail on the next leg of my journey.
> I will soon start a job where I will work with adjacent technology, and thus will seize to update the repos with new features.
> This is to not be questioned regarding IP going forward.
> 
> For the time being I want to let the codebases stay online, and will accept pull requests and occasionally do patch updates and bug fixes to > keep the solutions running.
> However, I will not take part in general feature discussions any longer, starting from 2024-11-01.
> 
> If you wish you may fork the projects and create features that you send me as pull requests. That way we can keep the flow going without > my direct interference in the inventions.
> For any usage not covered by the general download by hacs, look towards the license on the repos for guidance. Here's a snapshot of what > the licenses on my code requires: https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en
> 
> Thanks for all engagement and happy to have helped a bunch of people with this spare time invention of mine. 
> //Magnus

<img src="https://raw.githubusercontent.com/creativecommons/cc-assets/main/license_badges/big/by_nc_nd.svg" width="90">

[![Peaq_downloads](https://img.shields.io/github/downloads/elden1337/hass-peaqhvac/total)](https://github.com/elden1337/hass-peaqhvac) 
[![hass-peaqhvac_downloads](https://img.shields.io/github/downloads/elden1337/hass-peaqhvac/latest/total)](https://github.com/elden1337/hass-peaqhvac)
[![Paypal](https://img.shields.io/badge/Sponsor-PayPal-orange.svg)](https://www.paypal.com/donate/?hosted_button_id=GLGW8QAAQC2FG)
[![BuyMeACoffee](https://img.shields.io/badge/Sponsor-BuyMeACoffee-orange.svg)](https://buymeacoffee.com/elden)
[![Discord](https://img.shields.io/badge/Join-Discord-green.svg)](https://discord.gg/kgZzdsf4XA)

# Peaqhvac

<img src="https://raw.githubusercontent.com/elden1337/hass-peaq/main/assets/icon.png" width="125">


PeaqHvac is a custom component for Nibe F-series users. As of 2022-12-20 the tested versions are exhaust-air pumps F730 and F750, but it probably works fine with other similar ones as well.
In future releases other brands might be added.

Because of the slow response from the Nibe Uplink-api, calls are made somewhat prematurely to try and correct for this lag. 
If peakshaving is active _(requires PeaqEv)_ this means that peaks sometimes cannot be avoided completely, but rather lessened in their emphasis.


## Preparations

### Nibe 
_Nibe clients will need to have an uplink premium subscription in order to be able to manipulate the Hvac remotely._

It is required to have at least this setup in your `configuration.yaml`:

```yaml
nibe:
  systems:
    - system: 1234567890
      sensors:
        - 40995
        - 40997
        - 47206
```

* Set a heat-curve on your system that corresponds well to your desired level of heating at offset 0. Offsets is what PeaqHvac will manipulate
* Turn off indoor climate control on the heat pump as PeaqHvac now takes that role
* Turn off Nibe Smart Price Adaption if activated

### Integrations used

#### Required:
* [Nordpool](https://github.com/custom-components/nordpool) or [EnergiDataService](https://github.com/MTrab/energidataservice)
* Myuplink

#### Optional:
* Peak-shaving: [PeaqEv](https://github.com/elden1337/hass-peaq)
* Weather-prognosis: Met (with hourly sensor active)

## Installation
*Required to install is Home Assistant version 2023.10.5 or higher.*

Preferred if you have HACS installed is to search for Peaqhvac there.

Otherwise you may:
- Copy `custom_components/peaqhvac` folder to `<config_dir>/custom_components/peaqhvac/`
- Restart Home assistant
- Go to Configuration > Devices & Services > Add integration

### Configuration
_There are a few options when configuring PeaqHvac:_

| Name | Description                                                                                                                                           |
|------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Hvac systemid` | The provided system-id from your vendor. For Nibe F-series this is often a five digit number.                                                         |
| `Temp sensors indoors` | Your indoor temp sensor(s). Added as `sensor.`my_sensor. Comma-separated if many.                                                                     |
| `Temp sensors outdoors` | Your outdoor temp sensor(s). Added as `sensor.`my_sensor. Comma-separated if many.                                                                    |
| `Stop heating temp` | The outside temp where you never want Peaqhvac to start heating                                                                                       |
| `Very cold temp` | A very cold outside temp in your area, where Peaqhvac should start acting differently to save energy. _Not recommended to put value below -10C here._ |
| `Nonhours waterboost` | A selectable list of hours where you never wish to have a water-boost conducted _(not operational)_                                                   |
| `Low DM-value` | A number somewhere in between your Compressor-start and Electric addon start. Lower than this and Peaqhvac will take extra steps to conserve energy   |



## Functions

### Heating
PeaqHvac works with the common peaqevcore-library which is also used by PeaqEv to calculate good and bad hours of operation. What comes out of that is a set of offsets for today (and tomorrow if available) that are used to tune your hvac up/down accordingly.
After this calculation several things do happen, depending on the number of temperature-sensors used, if you want peak-shaving or not and if you have set up weather integration.

1. **Weather:** If peaqhvac detects an anomaly of more than 2.5C in the coming three hours from now, it will adjust the offset to pre-heat/pre-cold and make the curve more lean
2. **Temp diff:** Depending on your mode of operation, PeaqHvac is more or less forgiving towards temperature-changes. Normal operation for instance has a tolerance of -0.2C and +0.4C. These tolerances may also change depending on the base-offset. If the current indoor-temp breaches these thresholds, temp-diff will add/remove steps from the offset.
3. **Temp trend:** If the current trend of temperatures indoors tells the system that within an hour, it will breach the tolerances descired above, this function will add/remove steps.
4. **Temp extremas:** _If you have more than one indoor-tempsensor only_ This will add/deduct small fractions of steps based on how much of an extreme the very lowest/highest temps are compared to the mean. This function will rarely hit a full step-change, but gives an indication of how flat or jumpy your indoors temps are.

#### Key functions that do occur occasionally:
* **High ventilation at sunwarm:** If current temp is > 1C above set, and if both indoor and outdoor trends are rising heavily, the temperature will boost to take the "free" warm air into the system. _This happens down to a minimum of -5C_
* **High ventilation at low DM:** If the Degree-minutes drop below -700, the ventilation will boost to allow more air to flow into the system and overclock the compressor to its maximum frequency. _This happens down to a minimum of -12C_
* **Lower offset at low DM:** If the Degree-minutes drop below -700, the calculated offset will be lowered by 1 step.
* **Lower offset at Electrical addon:** If the Electrical addon is in use (for heating), the calculated offset will be lowered by 2 steps.
* **Lower offset at peak breach** (requires [PeaqEv](https://github.com/elden1337/hass-peaq))**:** If the projected consumption for the hour is above 100% of the registered max-peak and more than 30 minutes have passed, the calculated offset will be lowered by 1 step.
* **Peak hour turnoff:** If the current hour is the most expensive, and the temperature is more than 1C over set temp, a temporary offset of -10 will be pushed. This means that in most cases the pump will stop producing heat rather quickly. 

### Water

If control water is enabled a brief hot-waterboost will run (for ten minutes) when:
1. current offset is > 0 (relatively cheap hour) and watertemp is below 42C at approx 10 min past the hour
2. current offset is <= 0 (relatively expensive hour) and watertemp is below 30C at approx 10 min past the hour

Furthermore, when the cheapest hour in the known span occurs a real boost (up to the set boost-temp) will happen. This will often include a small amount of electrical addon.

_In future versions the hot water will get more love, for instance a secondary threshold to run boost or not (if cheap is not cheap enough) and to divert from certain hours alltogether despite the temp being too low._



## Included sensors

### Climate
`climate.peaqhvac_climate_control`

Set your desired temperature with this climate-control, in steps of half-degrees from 15-27C.
There are presets available in this sensor that you may set by automations or manually. They have different characteristics:
* `None` - Normal operation
* `Eco` - Reduced tolerance for increased temperatures before lowering offset. Will also reduce temperature by 0.1C per 1.5C if below -5C
* `Away` - Set temperature is lowered by 1C. Heavily reduced tolerance for increased temperatures before lowering offset. Will also reduce temperature by 0.1C per 1.5C if below -5C

### Sensors
* `number.peaqhvac_tolerance` - The number set here determines how well the offsets will align with the daily price-curve. Integers 1-10. **Remember that the higher the number, the higher the risk of electrical addon-usage and/or peak-energy hours.**
* `sensor.peaqhvac_calculated_hvac_offset` - This sensor will give you information on the currently calculated offset _(which is pushed to the Hvac if control heat is enabled)_. The attributes shows you the different calculation-steps to override a specific hourly offset based on the price. Here you may also retrieve the offsets for today, tomorrow plus the "raw" offsets for today that are without weather prognosis-interference.
* `sensor.peaqhvac_average_temperature_indoors`| `sensor.peaqhvac_average_temperature_outdoors` - The average temperatures based on the sensors you provide in setup.
* `sensor.peaqhvac_temperature_trend_indoors`| `sensor.peaqhvac_temperature_trend_outdoors` - The current temperature trends registered as C/h. 

### Switches
* `switch.peaqhvac_enabled` - This is the main switch to turn PeaqHvac on/off from your system.
* `switch.peaqhvac_control_heat` - If on, the heating will be controlled as described above
* `switch.peaqhvac_control_water` - If on, the water supply will be controlled as described above


