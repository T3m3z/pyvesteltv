# pyvesteltv

_pyvesteltv_ is a Python 3 library for interacting with Vestel television sets. Inspiration to create this library became from home automation project to allow [Home Assistant](https://home-assistant.io) integration. 

Vestel is a Turkish television manufacturer. Their brands include for example Procaster, Medion and Finlux.

**Note!** These television sets are quite cheap. This implicates "interesting" APIs and therefore some interactions with the TV might seem a bit "hackish" :)

Library has been tested only using Procaster LE-50F449.

## Supported features

* Turning TV on/off
* Selecting channel
* Changing volume
* Toggling mute
* Previous/next channel or track
* Various data about current state:
  * Mute status
  * Current channel
  * Current volume
  * Status of DIAL compatible apps (YouTube/Netflix)
