# -*- coding: utf-8 -*-
"""
pyVestelTV: Remote control of Vestel TV sets.
"""

from time import time
import asyncio
import aiohttp
from .broadcast import Broadcast
from websockets.exceptions import InvalidHandshake, InvalidURI, ConnectionClosed

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
        self.media = "Unknown"

        self.youtube = "stopped"
        self.netflix = "stopped"
        self.ws_state = ""

        self.reader = None
        self.writer = None
        self.websocket = None

        self.last_ws_msg = ""

        self._ws_connected = False
        self._tcp_connected = False

        self.debug_enabled = False

        self.ws_time = 0
        self.ws_counter = 0

        self.broadcast = Broadcast(self.loop,
                                   self.host,
                                   "ST: urn:dial-multiscreen-org:service:dial:1")
        coro = self.loop.create_datagram_endpoint(
            lambda: self.broadcast, local_addr=('0.0.0.0', 1900))
        self.loop.create_task(coro)

    def _debug(self, msg):
        """If debug enabled, print debug messages."""
        if self.debug_enabled:
            print(msg)

    async def _tcp_connect(self):
        """Try to connect to TV's TCP port."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host,
                                                                     self.tcp_port,
                                                                     loop=self.loop)
            self._tcp_connected = True
            self.state = True
        except TimeoutError:
            self._debug("TCP connect error")
            self._tcp_connected = False
            self._handle_off()

    async def _tcp_close(self):
        """Close TCP connection."""
        if self.writer:
            self.writer.close()
        self._tcp_connected = False

    async def _ws_connect(self):
        """Connect to TV via websocket protocol."""
        import websockets
        try:
            self.websocket = await websockets.connect('ws://%s:%s/' % (self.host, self.ws_port))
        except (InvalidHandshake, InvalidURI) as exp:
            self._debug("WS connect error: " + str(exp))
            self._handle_off()
            self._ws_connected = False
            return

        self.loop.create_task(self._ws_loop())
        self._ws_connected = True

    async def _ws_loop(self):
        """Run the websocket asyncio message loop."""
        try:
            while True:
                msg = await self.websocket.recv()
                msg = msg.strip()
                self._debug(msg)
                self.last_ws_msg = msg
                self._debug("Received WS msg: " + msg)
                if msg.startswith("<tv_state value='"):
                    data = msg.split("'")[1]
                    if not data and time() - self.ws_time < 1.5:
                        self.ws_counter += 1
                        if self.ws_counter >= 2:
                            self.state = False
                    elif not data:
                        self.ws_time = time()
                        self.ws_counter = 0
                        self.state = True
                    self.ws_state = data
                else:
                    msg = msg.split(":")
                    if msg[0] == "tv_status":
                        self.state = bool(msg[1])
        except ConnectionClosed as exp:
            self._debug("Error in _ws_loop: " + str(exp))
        finally:
            await self._ws_close()
            self._handle_off()

    async def _ws_close(self):
        """Close websocket connection."""
        if self.websocket:
            await self.websocket.close()
        self._ws_connected = False

    async def sendkey(self, key):
        """Send remote control key code over HTTP connction to virtual remote."""
        xml = "<?xml version=\"1.0\" ?><remote><key code=\"%d\"/></remote>" % key
        url = self.broadcast.get_app_url()
        if not url:
            return
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url + "vr/remote", data=xml) as _:
                    pass
        except aiohttp.ClientError:
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

    def discovered(self):
        """Returns boolean indicating if TV is discovered through DIAL."""
        return self.broadcast.discovered()

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
            self.state = True

    async def turn_off(self):
        """Turns the device off."""
        if self.state is True:
            await self.sendkey(1012)
            self.state = False

    async def toggle_mute(self):
        """Toggles mute."""
        await self.sendkey(1013)

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
        self.state = False
        self.youtube = "stopped"
        self.netflix = "stopped"

    async def update(self):
        """ Method to update state of the device."""
        self._debug("Update called")
        if not self.broadcast.discovered():
            self._debug("Not discovered -> turned off")
            self._handle_off()
        else:
            try:
                await asyncio.wait_for(self._read_data(), 5)
            except asyncio.futures.TimeoutError:
                self._handle_off()

    async def _read_data(self):
        """Private method for reading data."""
        if not self._ws_connected:
            self._debug("Trying to connect WS...")
            await self._ws_connect()
            self._debug("WS connect successful!")

        try:
            self._debug("!")
            if not self._tcp_connected:
                self._debug("Trying to connect TCP...")
                await self._tcp_connect()
                self._debug("TCP connect successful!")

            self.muted = await self._read_tcp_data("GETMUTE\r\n",
                                                   lambda x: True if x == "ON" else False)
            self.program = await self._read_tcp_data("GETPROGRAM\r\n")
            self.source = await self._read_tcp_data("GETSOURCE\r\n")
            self.volume = await self._read_tcp_data("GETHEADPHONEVOLUME\r\n", int)
            self._debug("TCP read ready!")
        except Exception as exp:
            await self._tcp_close()
            self._debug("TCP connect/read error: " + str(exp))

        try:
            self._debug("Trying to read state of applications...")
            self.youtube = await self._read_app_state("YouTube")
            self.netflix = await self._read_app_state("Netflix")
            self._debug("Application states updated!")
        except aiohttp.ClientError as exp:
            self._debug("Application state read failed: " + str(exp))

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

