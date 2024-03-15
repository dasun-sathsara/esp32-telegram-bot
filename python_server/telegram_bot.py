from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
)

from led_controller import LedController, LedState
from interfaces import IWebSocketServer
import asyncio
import logging


class TelegramBot:
    def __init__(self, admin: int, allowed_users: list[int]):
        self.context = None

        self.admin = admin
        self.allowed_users = set()
        self.allowed_users.add(admin)
        self.allowed_users.update(allowed_users)

    def _build_inline_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("LED: Blue 🔵", callback_data="blue"),
                InlineKeyboardButton("Led: Red  🔴", callback_data="red"),
            ],
            [InlineKeyboardButton("Turn Off LED 📴", callback_data="off")],
        ]

        return InlineKeyboardMarkup(keyboard)

    async def start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ws_server: IWebSocketServer,
        led_controller: LedController,
    ):
        # check if the user is allowed to use the bot
        if update.effective_user.id not in self.allowed_users:
            print(update.effective_chat.id)
            await update.message.reply_text("You are not allowed to use this bot.")
            return

        # check if the ESP32 is connected
        if not ws_server.is_connected():
            await update.message.reply_text("The ESP32 is not connected. Please try again later.")
            return

        # save the context
        self.context = context

        print(context.chat_data)

        # If a LED prompt message is already sent, delete it before sending a new one
        if "LED_PROMPT_MESSAGE_ID" in context.chat_data and context.chat_data["LED_PROMPT_MESSAGE_ID"] is not None:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, message_id=context.chat_data["LED_PROMPT_MESSAGE_ID"]
            )

        if led_controller.led_state == "error":
            message_text = "Choose a color to change the LED state."
        else:
            message_text = (
                f"LED State: {led_controller.led_state.capitalize()}\n\nChoose a color to change the LED state."
            )

        message = await update.message.reply_text(message_text, reply_markup=self._build_inline_keyboard())

        # Save the message ID in context.chat_data
        context.chat_data["LED_PROMPT_MESSAGE_ID"] = message.id
        print(context.chat_data)

    async def handle_change_led_state(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ws_server: IWebSocketServer,
        led_controller: LedController,
    ):
        query = update.callback_query
        new_led_state = query.data

        await query.answer()

        # reset the set event
        led_controller.set_event.clear()

        # send the new LED state to the ESP32 through the WebSocket server
        await ws_server.send(new_led_state)

        try:
            # wait for led_controller.set_event to be set or timeout after 4 seconds
            await asyncio.wait_for(led_controller.set_event.wait(), timeout=4)

            await query.edit_message_text(f"LED state changed to {led_controller.led_state.capitalize()}.")

        except asyncio.TimeoutError:
            logging.error("Timeout occurred while waiting for LED state change.")

            await query.edit_message_text(f"Timeout occurred while changing the LED state to {new_led_state}.")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

            try:
                await query.edit_message_text(
                    f"An unexpected error occurred while changing the LED state to {new_led_state}."
                )
            except:
                pass

        context.chat_data["LED_PROMPT_MESSAGE_ID"] = None

    async def broadcast_change_state(self, state: LedState):
        for user in self.allowed_users:
            try:
                await self.context.bot.send_message(user, f"LED state changed to {state.capitalize()}.")
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")
                continue
