"""
Example which toggles TV state.
"""

import asyncio
import pyvesteltv

LOOP = asyncio.get_event_loop()

ip_addr = input("Give TV IP address: ")

TV = pyvesteltv.VestelTV(LOOP, ip_addr)

async def update_state():
    """Updates state of the TV every 5 seconds."""
    while True:
        await TV.update()
        await asyncio.sleep(5)

async def tv_on_off():
    """Toggles TV every 5 seconds"""
    while True:
        await TV.turn_on()
        await asyncio.sleep(5)
        await TV.turn_off()
        await asyncio.sleep(5)

LOOP.create_task(update_state())
LOOP.create_task(tv_on_off())
LOOP.run_forever()
LOOP.close()
