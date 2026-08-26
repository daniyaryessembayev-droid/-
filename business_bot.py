import asyncio
import os
import io
import pandas as pd
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from google import genai
# Токены и ключи
BOT_TOKEN = "8358402574:AAGsZ-8M56rZ4bSyxBRCezdohQishgmx9LU"
GEMINI_KEY = "AIzaSyCyMLyTrizoxurkfrrm_4sR06SySPDN2KQ"

# Настройка подключения к Gemini API
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_salary_data = State()
    waiting_for_naming_data = State()

# Налоговые правила по законодательству Казахстана
KZ_TAX_RULES = """
Ты — профессиональный бухгалтер и финансовый аналитик по законодательству Республики Казахстан (РК).
При расчете или анализе зарплат/доходов ИП всегда опирайся на следующие стандартные ставки налогов и взносов РК:

1. Обязательные пенсионные взносы (ОПВ): 10% от начисленного дохода.
2. Индивидуальный подоходный налог (ИПН): 10% от облагаемого дохода (Начисленный доход - ОПВ - Стандартный вычет 14 МРП).
3. Социальные отчисления (СО): 3.5% от дохода (от 1 МЗП до 7 МЗП).
4. Взносы на ОСМС (ВОСМС с работника): 2% от дохода (максимум с 10 МЗП).
5. Отчисления на ОСМС (ООСМС от работодателя): 3% от дохода.
6. Налог по форме 910 (упрощенка для ИП): 3% от общего дохода (1.5% ИПН + 1.5% СН).

Если в документе представлена неструктурированная таблица, ведомость или отчёт (например, Зарплата к форме 910), распарси данные по людям, датам и суммам, приведи вычисления в порядок, рассчитай все необходимые налоги/проценты и составь понятную сводку.
"""

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Я ваш бизнес-бот и бухгалтер-помощник по законодательству РК.\n\n"
        "📊 Отправьте мне Excel/CSV файл (даже со сложной шапкой или неструктурированными данными), "
        "и я очищу данные, рассчитаю налоги, ОПВ, СО, ОСМС и дам подробный финансовый анализ."
    )

@dp.message(F.document)
async def handle_excel(message: types.Message):
    document = message.document
    file_name = document.file_name.lower()
    
    if not (file_name.endswith('.xlsx') or file_name.endswith('.xls') or file_name.endswith('.csv')):
        await message.answer("⚠️ Пожалуйста, отправьте файл формата Excel (.xlsx, .xls) или CSV.")
        return

    await message.answer("⏳ Обрабатываю и очищаю файл, рассчитываю налоги РК...")

    try:
        file_info = await bot.get_file(document.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        # Считывание и очистка файла от пустых объединений
        if file_name.endswith('.csv'):
            df = pd.read_csv(downloaded_file)
        else:
            df = pd.read_excel(downloaded_file, header=None)

        df = df.dropna(how='all').dropna(how='all', axis=1)

        formatted_text_list = []
        for row in df.values:
            clean_row = [str(val).strip() for val in row if pd.notna(val) and str(val).strip() != 'nan']
            if clean_row:
                formatted_text_list.append(" | ".join(clean_row))

        table_summary = "\n".join(formatted_text_list)

        if len(table_summary) > 5000:
            table_summary = table_summary[:5000] + "\n...[данные сокращены]"

        prompt = (
            f"{KZ_TAX_RULES}\n\n"
            f"Вот данные из полученного документа/таблицы (файл: {document.file_name}):\n\n"
            f"{table_summary}\n\n"
            "Задание:\n"
            "1. Распознай структуру данных, даже если шапка таблицы была нестандартной.\n"
            "2. Сделай подробный расчет налогов, отчислений (ОПВ, СО, ВОСМС, ИПН) и итоговых сумм по законодательству РК.\n"
            "3. Выведи итоговые выводы, таблицы и рекомендации понятным языком."
        )

        response = model.generate_content(prompt)

        text_response = response.text
        if len(text_response) > 4000:
            for x in range(0, len(text_response), 4000):
                await message.answer(text_response[x:x+4000])
        else:
            await message.answer(text_response)

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
