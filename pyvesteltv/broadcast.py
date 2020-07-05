from time import time
import aiohttp

class Broadcast:
    """Broadcast class used for discovery purposes and maintaining correct device state."""

    def __init__(self, loop, host=None, msg="", broadcast_interval = 5, discovery_retries = 3):
        """Init broadcast class."""
        self.loop = loop
        self.url = None
        self.last_discovery = 0
        self.broadcast_interval = broadcast_interval
        self.discovery_timeout = discovery_retries*self.broadcast_interval + 1
        self.msg = msg.encode()
        self.host = host
        self.transport = None

    def connection_made(self, transport):
        """MMethod called after socket creation."""
        self.transport = transport
        if self.msg:
            self.broadcast()

    def datagram_received(self, data, addr):
        """Handles incoming messages."""
        if self.host is None or addr[0] == self.host:
            for i in data.decode().split("\r\n"):
                if i.startswith("LOCATION:"):
                    url = i.split(": ")[1]
                    self.loop.create_task(self.handle_url(url))
                    break

    async def handle_url(self, url):
        """Retrieves DIAL Application-URL if possible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    self.url = resp.headers["Application-URL"]
                    self.last_discovery = time()
        except aiohttp.ClientError:
            self.last_discovery = 0

    def get_app_url(self):
        """Returns discovered application url (if still valid)."""
        if time() - self.last_discovery > self.discovery_timeout:
            return None
        return self.url

    def discovered(self):
        """Returns boolean indicating if device was discovered lately."""
        return time() - self.last_discovery < self.discovery_timeout

    def broadcast(self):
        """Broadcasting of DIAL message."""
        self.transport.sendto(self.msg, ('239.255.255.250', 1900))
        self.loop.call_later(self.broadcast_interval, self.broadcast)
