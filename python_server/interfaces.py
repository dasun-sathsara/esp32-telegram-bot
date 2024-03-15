from abc import ABC, abstractmethod
from led_controller import LedController, LedState
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


class IWebSocketServer(ABC):
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    async def send(self, state: LedState):
        pass


class ITelegramBot(ABC):
    @abstractmethod
    def _build_inline_keyboard(self) -> InlineKeyboardMarkup:
        pass

    @abstractmethod
    async def start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ws_server: IWebSocketServer,
        led_controller: LedController,
    ):
        pass

    @abstractmethod
    async def handle_change_led_state(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        ws_server: IWebSocketServer,
        led_controller: LedController,
    ):
        pass

    @abstractmethod
    async def broadcast_change_state(self, state: LedState):
        pass
