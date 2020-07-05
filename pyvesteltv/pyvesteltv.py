# -*- coding: utf-8 -*-
"""
pyVestelTV: Remote control of Vestel TV sets.
"""

from time import time
import logging
import asyncio
import aiohttp
from .broadcast import Broadcast
from websockets.exceptions import InvalidHandshake, InvalidURI, ConnectionClosed

_LOGGER = logging.getLogger(__name__)

# pylint: disable=too-many-instance-attributes
class VestelTV:
    """Class for interacting with Vestel smart TVs."""

    def __init__(self, loop, host, timeout=5):
        """Init Library."""
        self.loop = loop
        self.host = host
        self.timeout = timeout
        self.tcp_port = 1986
        self.ws_port = 7681

        self.state = False
        self.volume = 0
        self.muted = False
        self.program = "Unknown"
        self.source = "Unknown"

        self.youtube = "stopped"
        self.netflix = "stopped"
        self.ws_state = ""
        
        self.colour = 0
        self.sharpness = 0
        self.contrast = 0
        self.brightness = 0

        self.reader = None
        self.writer = None
        self.websocket = None

        self.last_ws_msg = ""

        self.ws_time = 0
        self.ws_counter = 0

        self.broadcast = Broadcast(self.loop,
                                   self.host,
                                   "ST: urn:dial-multiscreen-org:service:dial:1")
        coro = self.loop.create_datagram_endpoint(
            lambda: self.broadcast, local_addr=('0.0.0.0', 1900))
        self.loop.create_task(coro)

    async def _tcp_connect(self):
        """Try to connect to TV's TCP port."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host,
                                                                     self.tcp_port,
                                                                     loop=self.loop)
            self.set_state(True, "TCP Connect")
        except TimeoutError:
            _LOGGER.error("TCP connect TimeoutError")
            self.writer = None

    async def _tcp_close(self):
        """Close TCP connection."""
        if self.writer:
            self.writer.close()
            self.writer = None

    async def _ws_connect(self):
        """Connect to TV via websocket protocol."""
        import websockets
        try:
            self.websocket = await websockets.connect('ws://{}:{}/'.format(self.host, self.ws_port))
            self.loop.create_task(self._ws_loop())
        except (InvalidHandshake, InvalidURI) as exp:
            _LOGGER.error("WS connect error: ", exc_info=True)

    async def _ws_loop(self):
        """Run the websocket asyncio message loop."""
        try:
            while True:
                msg = await self.websocket.recv()
                msg = msg.strip()
                self.last_ws_msg = msg
                _LOGGER.debug("Received WS msg: " + msg)
                if msg.startswith("<tv_state value='"):
                    data = msg.split("'")[1]
                    self.set_state(True, "_ws_loop 1")
                    if not data and time() - self.ws_time < 1.5:
                        self.ws_counter += 1
                        if self.ws_counter >= 2:
                            self.set_state(False, "_ws_loop 2")
                    elif not data:
                        self.ws_time = time()
                        self.ws_counter = 0
                    elif data:
                        self.ws_time = 0
                    self.ws_state = data
                else:
                    msg = msg.split(":")
                    if msg[0] == "tv_status":
                        self.set_state(msg[1] == "1", "tv_status dynamic")
        except ConnectionClosed as exp:
            _LOGGER.info("Error in _ws_loop: ", exc_info=True)
        finally:
            await self._ws_close()

    async def _ws_close(self):
        """Close websocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def sendkey(self, key):
        """Send remote control key code over HTTP connction to virtual remote."""
        xml = "<?xml version=\"1.0\" ?><remote><key code=\"{}\"/></remote>".format(key)
        url = self.broadcast.get_app_url()
        if not url:
            return
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url + "vr/remote", data=xml) as _:
                    pass
        except aiohttp.ClientError:
            _LOGGER.warning("Error sending key code {}".format(key))
            pass

    def get_volume(self):
        """Returns current volume level (0..1)."""
        return self.volume / 100

    def get_state(self):
        """Returns boolean indicating if TV is turned on."""
        return self.state

    def get_program(self):
        """Returns current/last TV channel name."""
        return self.program

    def get_muted(self):
        """Returns boolean indicating if TV is muted"""
        return self.muted
        
    def get_colour(self):
        """Returns colour value"""
        return self.colour
    
    def get_sharpness(self):
        """Returns sharpness value"""
        return self.sharpness
        
    def get_contrast(self):
        """Returns contrast value"""
        return self.contrast
        
    def get_brightness(self):
        """Returns brightness value"""
        return self.brightness

    def get_websocket_state(self):
        return self.websocket is not None and self.websocket.open

    def discovered(self):
        """Returns boolean indicating if TV is discovered through DIAL."""
        return self.broadcast.discovered()
        
    async def start_youtube(self):
        """Start YouTube using DIAL"""
        url = self.broadcast.get_app_url()
        if url:
            async with aiohttp.ClientSession() as session:
                async with session.post(url + "YouTube") as _:
                    pass

    async def stop_youtube(self):
        """Stop YouTube by changing source"""
        await self.sendkey(1056)

    async def start_netflix(self):
        """Start Netflix using DIAL"""
        url = self.broadcast.get_app_url()
        if url:
            async with aiohttp.ClientSession() as session:
                async with session.post(url + "Netflix") as _:
                    pass

    async def stop_netflix(self):
        """Stop Netflix using DIAL"""
        url = self.broadcast.get_app_url()
        if url:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url + "Netflix/run") as _:
                    pass

    async def volume_up(self):
        """Increase volume by one step."""
        await self.sendkey(1016)

    async def volume_down(self):
        """Decrease volume by one step."""
        await self.sendkey(1017)

    async def set_volume(self, volume):
        """Simulates setting volume by calling volume steps multiple times."""
        for _ in range(abs(int(volume*100)-self.volume)):
            if int(volume*100) > self.volume:
                await self.volume_up()
            else:
                await self.volume_down()

    async def previous_track(self):
        """Simulates press of P- or Previous Track depenging on current source."""
        title = self.get_media_title()
        if title.startswith("TV"):
            await self.sendkey(1033)
        else:
            await self.sendkey(1027)

    async def next_track(self):
        """Simulates press of P+ or Next Track depenging on current source."""
        title = self.get_media_title()
        if title.startswith("TV"):
            await self.sendkey(1032)
        else:
            await self.sendkey(1028)

    async def turn_on(self):
        """Turns the device on."""
        if self.state is False:
            await self.sendkey(1012)
            self.set_state(True, "turn_on")

    async def turn_off(self):
        """Turns the device off."""
        if self.state is True:
            await self.sendkey(1012)
            self.set_state(False, "turn_off")

    async def toggle_mute(self):
        """Toggles mute."""
        await self.sendkey(1013)

    def set_state(self, state, info = ""):
        _LOGGER.debug("Changed state from {} to {}. Info: {}".format(self.state, state, info))
        self.state = state       

    def get_media_title(self):
        """Return the current media title."""
        if self.youtube == "running":
            title = "YouTube"
        elif self.netflix == "running":
            title = "Netflix"
        elif self.state is False:
            title = None
        elif self.ws_state == "NOSIGNAL":
            title = self.source + "/" + self.ws_state
        elif self.ws_state != "":
            title = self.ws_state
        elif self.source == "TV":
            title = "TV: " + self.program
        else:
            title = "Source: " + self.source
        return title

    def _handle_off(self):
        """Sets various variables to off-state."""
        _LOGGER.info("Handle_off() called")
        self.set_state(False, "handle_off")
        self.youtube = "stopped"
        self.netflix = "stopped"

    async def update(self):
        """ Method to update state of the device."""
        _LOGGER.debug("Device state update initiated.")
        if not self.broadcast.discovered():
            _LOGGER.debug("Device not discovered. Turned off.")
            if self.state == True:
                self._handle_off()
            if self.writer:
                _LOGGER.info("Not discovered, closing TCP connection")
                await self._tcp_close()
            if self.websocket:
                _LOGGER.info("Not discovered, closing WS connection")
                await self._ws_close()                
        else:
            try:
                await asyncio.wait_for(self._read_data(), 5)
            except asyncio.futures.TimeoutError:
                self._handle_off()

    async def _read_data(self):
        """Private method for reading data."""
        if not self.get_websocket_state():
            _LOGGER.info("Trying to connect WS...")
            await self._ws_connect()
            _LOGGER.info("WS connect successful!")
        else:
            pong_waiter = await self.websocket.ping()
            await pong_waiter

        try:
            if not self.writer:
                _LOGGER.debug("Trying to connect TCP...")
                await self._tcp_connect()
                _LOGGER.debug("TCP connect successful!")

            self.muted = await self._read_tcp_data("GETMUTE\r\n",
                                                   lambda x: True if x == "ON" else False)
            self.program = await self._read_tcp_data("GETPROGRAM\r\n")
            self.source = await self._read_tcp_data("GETSOURCE\r\n")
            self.volume = await self._read_tcp_data("GETHEADPHONEVOLUME\r\n", int)
            self.colour = await self._read_tcp_data("GETCOLOUR\r\n", int)
            self.contrast = await self._read_tcp_data("GETCONTRAST\r\n", int)
            self.sharpness = await self._read_tcp_data("GETSHARPNESS\r\n", int)
            self.brightness = await self._read_tcp_data("GETBRIGHTNESS \r\n", int)
            _LOGGER.debug("TCP read ready!")
        except Exception as exp:
            await self._tcp_close()
            _LOGGER.warning("TCP connect/read error:", exc_info=True)

        try:
            _LOGGER.debug("Trying to read state of applications...")
            self.youtube = await self._read_app_state("YouTube")
            self.netflix = await self._read_app_state("Netflix")
            _LOGGER.debug("Application states updated!")
        except aiohttp.ClientError as exp:
            _LOGGER.error("Application state read failed:", exc_info=True)

        # FOLLOWING TCP commands could be added:
        # GETSTANDBY
        # GETCHANNELLISTVIEW
        # GETBACKLIGHT
        # GETPICTUREMODE
        # GETCONTRAST
        # GETSHARPNESS
        # GETCOLOUR

    async def _read_tcp_data(self, msg, func=str):
        """Private method for reading TCP data."""
        self.writer.write(msg.encode())
        data = await self.reader.readline()
        row = data.decode().strip()
        if " is " in row:
            return func(row.split(" is ")[-1])
        return func(row.split(" ")[-1])

    async def _read_app_state(self, appname):
        """Private method for reading DIAL information of specific app."""
        import xml.etree.ElementTree as ET
        url = self.broadcast.get_app_url()
        if url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url + appname) as resp:
                        text = await resp.text()
                        root = ET.fromstring(text)
                        return root[2].text
            except aiohttp.ClientError:
                pass
        return "stopped"
