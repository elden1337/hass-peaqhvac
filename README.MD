[![hacs_badge](https://img.shields.io/badge/HACS-Default-brightgreen.svg)](https://github.com/hacs/integration) 
![Validate with hassfest](https://github.com/elden1337/hass-peaqhvac/workflows/Validate%20with%20hassfest/badge.svg) 
[![Peaq_downloads](https://img.shields.io/github/downloads/elden1337/hass-peaqhvac/total)](https://github.com/elden1337/hass-peaq) 
[![hass-peaq_downloads](https://img.shields.io/github/downloads/elden1337/hass-peaqhvac/latest/total)](https://github.com/elden1337/hass-peaq)
[![Buy me a coffee](https://img.shields.io/static/v1.svg?label=Buy%20me%20a%20coffee&message=🥨&color=black&logo=buy%20me%20a%20coffee&logoColor=white&labelColor=6f4e37)](https://www.buymeacoffee.com/elden)
# Peaqhvac

![Peaq logo](https://raw.githubusercontent.com/elden1337/hass-peaq/main/assets/icon.png)

Peaqhvac

This integration does not communicate with any properitary API's, everything is handled locally in your Home Assistant.

*While this integration will try to not break your monthly energy peak hour, there is off course no guarantee. Various factors beyond control of this logic do occur, so for those aiming at staying below their threshold, I do suggest you think about the non-hours, caution-hours etc in the setup. These hours should be set when you commonly utilize a lot of extra energy in your home, such as cooking, doing laundry etc.* 

## Installation
*Required to install is Home Assistant version 2022.4.5 or higher.*

Preferred if you have HACS installed is to search for Peaqhvac there.

Otherwise you may:
- Copy `custom_components/peaqhvac` folder to `<config_dir>/custom_components/peaqhvac/`
- Restart Home assistant
- Go to Configuration > Devices & Services > Add integration

### Config setup:


## Usage

- To start and stop, I suggest you create automations that call the services `peaqev.enable` and `peaqev.disable`. 
- Make sure to not exclude the created sensors from your recorder, as this would conflict with the monthly peaks.

Example of basic automations to enable/disable the charging. Your states here may differ from the example which is a Chargeamps Halo:
```yaml
- id: '111111'
  alias: Peaq - Charge
  trigger:
  - platform: state
    entity_id: sensor.your_chargersensor
    from: Available
    to: Connected
  - service: peaqev.enable
    data: {}
  mode: single

- id: '222222'
  alias: Peaq - Disconnected
  trigger:
  - platform: state
    entity_id: sensor.your_chargersensor
    to: Available
  condition: []
  action:
  - service: peaqev.disable
    data: {}
  mode: single
```

*Tested with Chargeamps Halo 11kw and Easee. Both setups with one single charger per household. Currently will not function where multiple chargers have been installed ,2022-05-16*


