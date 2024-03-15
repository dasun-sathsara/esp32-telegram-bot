import asyncio
import logging
import os
import signal
import ssl

from functools import partial

import websockets
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
)

from websocket_server import WebSocketServer
from led_controller import LedController
from telegram_bot import TelegramBot

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    led_controller = LedController()
    ws_server = WebSocketServer()
    tg_bot = TelegramBot(int(os.getenv("ADMIN_USER_ID")), [])

    # initialize a telegram application with the bot token
    tg_application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    # '/start' command handler
    start_handler = CommandHandler("start", partial(tg_bot.start, ws_server=ws_server, led_controller=led_controller))

    # callback query handler for the LED color change prompt
    led_color_button_handler = CallbackQueryHandler(
        partial(tg_bot.handle_change_led_state, ws_server=ws_server, led_controller=led_controller)
    )

    tg_application.add_handler(start_handler)
    tg_application.add_handler(led_color_button_handler)

    await tg_application.initialize()
    await tg_application.start()
    await tg_application.updater.start_polling()

    # setup Websocket Server
    loop = asyncio.get_event_loop()

    # future to signal server shutdown. It will be set when SIGINT is received
    stop_server = loop.create_future()

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        certfile="", # path to the certificate file
        keyfile="",  # path to the private key file 
    )

    # register SIGINT handler to stop the server
    loop.add_signal_handler(signal.SIGINT, stop_server.set_result, None)

    ws_server = await websockets.serve(
        partial(ws_server.register, led_controller=led_controller, tg_bot=tg_bot),
        "", # host
        443,
        ssl=ssl_context,
    )

    await stop_server  # wait until the server should stop

    # close the server
    ws_server.close()
    await ws_server.wait_closed()

    # close the telegram bot
    await tg_application.updater.stop()
    await tg_application.stop()
    await tg_application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
