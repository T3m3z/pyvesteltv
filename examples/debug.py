"""
Example which enables debug prints.
"""

import asyncio
import pyvesteltv

LOOP = asyncio.get_event_loop()

ip_addr = input("Give TV IP address: ")

TV = pyvesteltv.VestelTV(LOOP, ip_addr)

async def update_state():
    """Updates state of the TV every 5 seconds."""
    await TV.update()
    print(TV.get_state())
    await asyncio.sleep(5)
    LOOP.create_task(update_state())

LOOP.create_task(update_state())
LOOP.run_forever()
LOOP.close()
