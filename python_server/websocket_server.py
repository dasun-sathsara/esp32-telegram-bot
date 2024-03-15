from websockets import WebSocketServerProtocol
from led_controller import LedController, LedState
import json
import logging

from interfaces import ITelegramBot


class WebSocketServer:
    def __init__(self):
        self.client = None  # only one client will be connected (ESP32)

    def is_connected(self) -> bool:
        return self.client is not None

    async def send(self, state: LedState):
        message = json.dumps({"state": state, "type": "tg_change_state"})

        try:
            await self.client.send(message)
            logging.info(f"Message sent to ESP32: {message}")
        except Exception as e:
            logging.error(f"An error occurred while sending message to ESP32: {e}")

    async def _handle_ws_messages(self, led_controller: LedController, tg_bot: ITelegramBot):
        async for message in self.client:
            logging.info(f"Message received from ESP32: {message}")

            event = json.loads(message)

            # If the change state event originated from the Telegram bot
            if event["type"] == "tg_change_state":
                # this will set the event, notifying the handle_change_led_state coroutine
                led_controller.change_state(event["state"])

            # If the change state event originated from the ESP32
            elif event["type"] == "esp32_change_state":

                if led_controller.led_state != event["state"]:
                    led_controller.change_state(event["state"])
                    await tg_bot.broadcast_change_state(event["state"])

    async def register(self, websocket: WebSocketServerProtocol, led_controller: LedController, tg_bot: ITelegramBot):
        logging.info("WebSocket client connected.")
        self.client = websocket

        await self._handle_ws_messages(led_controller, tg_bot)
