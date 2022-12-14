<img src="https://raw.githubusercontent.com/creativecommons/cc-assets/main/license_badges/big/by_nc_nd.svg" width="90">

[![Peaq_downloads](https://img.shields.io/github/downloads/elden1337/hass-peaqhvac/total)](https://github.com/elden1337/hass-peaqhvac) 
[![hass-peaqhvac_downloads](https://img.shields.io/github/downloads/elden1337/hass-peaqhvac/latest/total)](https://github.com/elden1337/hass-peaqhvac)
[![Paypal](https://img.shields.io/badge/Sponsor-PayPal-orange.svg)](https://www.paypal.com/donate/?hosted_button_id=GLGW8QAAQC2FG)
[![BuyMeACoffee](https://img.shields.io/badge/Sponsor-BuyMeACoffee-orange.svg)](https://buymeacoffee.com/elden)
[![Discord](https://img.shields.io/badge/Join-Discord-green.svg)](https://discord.gg/kgZzdsf4XA)

# Peaqhvac

<img src="https://raw.githubusercontent.com/elden1337/hass-peaq/main/assets/icon.png" width="125">

### INTROTEXT
Peaqev is developed without static funding. If you lack your locale/charger type or have wishes for other specific features that you would like to see prioritized, please consider becoming a [Github sponsor](https://github.com/sponsors/elden1337) to bump your desired changes in my backlog.
- In order to flag a ticket, either create a new one or comment on an existing one after you've started your sponsorship. I will then flag the ticket with `sponsored-change` and try to prioritize this going forward
- Becoming a sponsor is not a guarantee that a wish will be created, or a guarantee for a specified resolution time. Peaqev is being developed in my spare time and every feature has to be considered by me before taking it into development
- I may need to reach out for testing, especially if your wish includes implementing new charger types
- Critical bugs discovered of course always triages higher than features

:love_letter:

---

For Nibe it is required to have at least this setup in your `configuration.yaml`:

```yaml
nibe:
  systems:
    - system: 1234567890
      sensors:
        - 40995
        - 40997
        - 47206
```

* If you wish to allow peak-shaving you will need to have PeaqEv installed. This will change in future versions.
* If you wish to adhere to weather prognosis, you must have the Met-integration installed, and allow hourly sensor.
