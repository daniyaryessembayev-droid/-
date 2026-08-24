import asyncio
import os
from aiohttp import web          
import pandas as pd
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from google import genai

# Вставьте ваши ключи
BOT_TOKEN = "8358402574:AAGsZ-8M56rZ4bSyxBRCezdohQishgmx9LU"
GEMINI_KEY = "AIzaSyCYmLyTrizoxurkfrrm_4sR06SySPDN2KQ"

ai_client = genai.Client(api_key=GEMINI_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_salary_data = State()
    waiting_for_naming_data = State()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Я бизнес-бот.\n\n"
        "• Отправьте мне **Excel-файл (.xlsx)**, и я передам его на анализ в Gemini.\n"
        "• Или отправьте текстовый запрос для расчета / нейминга.",
        parse_mode="Markdown"
    )

# Обработка Excel файлов
@dp.message(F.document)
async def handle_excel(message: types.Message):
    file_name = message.document.file_name
    if not file_name.endswith(('.xlsx', '.xls', '.csv')):
        await message.answer("❌ Пожалуйста, отправьте файл формата .xlsx, .xls или .csv")
        return

    await message.answer("📥 Скачиваю и анализирую таблицу...")
    
    try:
        file_info = await bot.get_file(message.document.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        # Чтение таблицы через pandas
        if file_name.endswith('.csv'):
            df = pd.read_csv(downloaded_file)
        else:
            df = pd.read_excel(downloaded_file)
            
        # Берем первые строки таблицы для анализа нейросетью
        table_summary = df.head(50).to_string(index=False)
        
        prompt = f"Проанализируй данные из этой таблицы (показаны первые строки), сделай выводы, расчеты или дай рекомендации:\n\n{table_summary}"
        
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        await message.answer(f"📊 **Результат анализа таблицы:**\n\n{response.text}", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла: {e}")

async def handle(request):
    return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
