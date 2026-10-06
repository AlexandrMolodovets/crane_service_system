import asyncio
import logging
import os

from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, MessageCreated

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен лучше хранить в переменной окружения, но для теста можно вставить строкой
# Не забудьте заменить на реальный токен после модерации
bot = Bot(token="f9LHodD0cOIeEXgxD_yosX5wO_syF_T8shC9RUmTXd3FtMAZ6sbSpHHJ7AxNDRzLMPDvOKvWM615QZwpAjjS") 
dp = Dispatcher()

# Ответ на кнопку "Начать" (BotStarted)
@dp.bot_started()
async def bot_started(event: BotStarted):
    await bot.send_message(
        chat_id=event.chat_id, 
        text="Привет! Я бот для обслуживания кранов. Отправь /start"
    )

# Ответ на команду /start
@dp.message_created(CommandStart())
async def hello(event: MessageCreated):
    await event.message.answer("Система ПТО на связи 💙 Отправь мне любой текст, и я его повторю.")

# Эхо-ответ на любое текстовое сообщение (фильтр F.message.body.text)
@dp.message_created(F.message.body.text)
async def echo(event: MessageCreated):
    await event.message.answer(event.message.body.text)

async def main():
    print("🚀 Бот запущен. Нажмите Ctrl+C для остановки.")
    # ⚠️ Polling подходит ТОЛЬКО для тестов.
    # Для production (постоянной работы) нужен Webhook.
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())