import asyncio
from typing import Literal

LedState = Literal["red", "blue", "off", "error"]


class LedController:
    def __init__(self):
        self.led_state: LedState = "off"

        # event will be set when the state of the LED is changed. listeners can wait for this event to be set.
        self.set_event = asyncio.Event()

    # this method will be called by the WebSocketServer when a new state is received from the ESP32.
    # change of state could happen as a response to a user action (telegram bot) or a direct action from the ESP32
    def change_state(self, state: LedState):
        self.led_state = state
        self.set_event.set()
