import asyncio
import json
import logging
import os
from datetime import datetime

from fastapi import FastAPI
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.context import MemoryContext  # ← ИСПРАВЛЕНО: context вместо fsm
from maxapi.types import BotStarted, MessageCreated, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton, LinkButton
from supabase import create_client

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота из переменных окружения (Railway)
BOT_TOKEN = "f9LHodD0cOJ6_iht9e5VVGmhqPH8-vKcn8YcGHULls6r0SWQfGo8u_U0mavZT8UeC2sE0kgEwC4Cwe_8caI0"
if not BOT_TOKEN:
    raise ValueError("Переменная окружения MAX_BOT_TOKEN не задана")

# Supabase — временно вписаны прямо в код (для локального теста)
SUPABASE_URL = "https://mkrhnmnleisforgghhfi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rcmhubW5sZWlzZm9yZ2doaGZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg5MTU2MjAsImV4cCI6MjA2NDQ5MTYyMH0.6y4iB0JWjfP9VNK-6lwCahE36dXgXrQbLkDqT7YgZno"

supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# FSM-контекст для хранения состояний диалога [citation:1][citation:10]
# fsm_context = MemoryContext(ttl=3600)  # Автоочистка неактивных контекстов через час


# ========== ОБРАБОТЧИКИ ==========

# Обработчик нажатия "Создать заявку"
@dp.message_callback(F.message_callback.payload == "new_request")
async def start_new_request(event: MessageCallback, context: MemoryContext):
    await event.answer()
    
    chat_id = event.message.recipient.chat_id
    user_id = event.message.sender.user_id
    
    # Устанавливаем состояние
    await context.set_state("waiting_for_crane_number")
    await context.set_data({})
    
    await bot.send_message(
        chat_id=chat_id,
        text="Введите номер крана (например, ПК-123):"
    )


# Обработчик текстовых сообщений
@dp.message_created(F.message.body.text)
async def handle_text_input(event: MessageCreated, context: MemoryContext):
    chat_id = event.message.recipient.chat_id
    user_id = event.message.sender.user_id
    text = event.message.body.text
    
    # Получаем состояние и данные из контекста
    state = await context.get_state()
    data = await context.get_data()
    
    if state == "waiting_for_crane_number":
        data["crane_number"] = text
        await context.set_data(data)
        await context.set_state("waiting_for_location")
        await event.message.answer("Введите место нахождения крана:")
    
    elif state == "waiting_for_location":
        data["location"] = text
        await context.set_data(data)
        await context.set_state("waiting_for_description")
        await event.message.answer("Опишите проблему или замечание:")
    
    elif state == "waiting_for_description":
        data["description"] = text
        data["user_id"] = user_id
        
        report_id = await save_request_to_supabase(data)
        await context.clear()
        
        if report_id:
            await event.message.answer(
                f"✅ Заявка создана!\n📋 ID: {report_id}\n🚧 Кран: {data.get('crane_number', '')}"
            )
        else:
            await event.message.answer("❌ Ошибка при создании заявки.")
    
    else:
        await event.message.answer(text)


# ========== СОХРАНЕНИЕ В SUPABASE ==========

async def save_request_to_supabase(data: dict) -> int:
    """Сохраняет заявку из бота в таблицу crane_reports"""
    try:
        report_data = {
            "inspection_date": datetime.now().strftime("%Y-%m-%d"),
            "crane_type": "Портальный",
            "crane_number": data.get("crane_number", "Не указан"),
            "location": data.get("location", "Не указано"),
            "journal_remarks": data.get("description", ""),
            "repair_work_done": "",
            "service_data": json.dumps({}),
            "hidden_defects": "",
            "conclusion": "operational",
            "technician_name": f"Из MAX-бота (ID: {data.get('user_id', 'unknown')})"
        }

        result = supabase_client.table("crane_reports").insert(report_data).execute()

        if result.data:
            return result.data[0]["id"]
        return None
    except Exception as e:
        print(f"❌ Ошибка сохранения в Supabase: {e}")
        return None


# ========== WEBHOOK (FastAPI) ==========

# Создаём FastAPI приложение и подключаем к нему Webhook [citation:7]
app = FastAPI()

# maxapi автоматически обрабатывает webhook через FastAPI
@app.post("/webhook")
async def webhook_handler(request):
    """Обработчик Webhook-запросов от MAX"""
    from fastapi import Request
    body = await request.json()
    await dp.handle_webhook_update(bot, body)
    return {"status": "ok"}


@app.get("/")
async def health_check():
    """Проверка работоспособности"""
    return {"status": "ok", "service": "Crane Service Bot"}


# ========== ЗАПУСК ==========

if __name__ == "__main__":
    import uvicorn

    PORT = int(os.getenv("PORT", 8080))
    print(f"🚀 Бот запущен на порту {PORT}")
    print(f"📡 Webhook endpoint: http://0.0.0.0:{PORT}/webhook")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
