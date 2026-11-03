import os
from aiohttp import web
import asyncio
import sqlite3
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ==================== НАСТРОЙКИ ПРОЕКТА ====================
BOT_TOKEN = "8675874135:AAFgO_SFaKsnOGJG3GuuG99q-WankLB93vU"

# Ссылки на твои статьи в Telegra.ph
PRIVACY_URL = "https://telegra.ph/Data-vstupleniya-v-silu-04112026-11-03"
TERMS_URL = "https://telegra.ph/Data-vstupleniya-v-silu-04112026-11-03-2"

SUPPORT_TG = "@manedgerO"
SUPPORT_EMAIL = "supportramvpn@gmail.com"
EFFECTIVE_DATE = "04.11.2026"

# ==================== ТАРИФНАЯ СЕТКА ====================
TARIFFS = {
    "base": {
        "title": "🛡 RAM Base (Германия)",
        "locations": "🇩🇪 Франкфурт (Германия)",
        "features": (
            "• <b>1 выделенная локация:</b> Германия 🇩🇪\n"
            "• Протокол шифрования: VLESS / Reality (256-bit)\n"
            "• Защита трафика в публичных Wi-Fi сетях\n"
            "• Пропускная способность: до 300 Мбит/с\n"
            "• Безлимитный трафик на 1-2 устройства"
        ),
        "plans": {
            "base_1m": {"period": "1 месяц", "price": 149},
            "base_6m": {"period": "6 месяцев", "price": 599},
            "base_1y": {"period": "1 год", "price": 1499},
        }
    },
    "pro": {
        "title": "⚡ RAM Pro (Мульти-регион)",
        "locations": "🇸🇪 Швеция, 🇫🇷 Франция, 🇺🇸 США, 🇫🇮 Финляндия, 🇩🇪 Германия",
        "features": (
            "• <b>5 премиум-локаций:</b> Швеция, Франция, США, Финляндия, Германия\n"
            "• Свободное переключение между дата-центрами\n"
            "• Пропускная способность: до 1 Гбит/с\n"
            "• Минимальный пинг для стриминга и гейминга\n"
            "• Поддержка до 5 устройств одновременно"
        ),
        "plans": {
            "pro_1m": {"period": "1 месяц", "price": 499},
            "pro_6m": {"period": "6 месяцев", "price": 1999},
            "pro_1y": {"period": "1 год", "price": 3999},
        }
    },
    "ultra": {
        "title": "💎 RAM Ultra AI (Выделенные серверы)",
        "locations": "🌐 Приоритетный кластер (EU + US Dedicated)",
        "features": (
            "• <b>Выделенные мощные серверы (Dedicated Core)</b>\n"
            "• Полная совместимость и оптимизация под <b>Google Gemini</b> и другие AI-платформы\n"
            "• Выделенный канал до 10 Гбит/с без просадок скорости\n"
            "• Максимальная криптографическая защита и чистые IP-адреса\n"
            "• Приоритетное обслуживание 24/7 (VIP-поддержка)"
        ),
        "plans": {
            "ultra_1y": {"period": "1 год (Максимальный пакет)", "price": 7000},
        }
    }
}

# ==================== БАЗА ДАННЫХ (SQLite) ====================
def init_db():
    conn = sqlite3.connect("ram_vpn.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            reg_date TEXT,
            active_plan TEXT DEFAULT 'Не активна'
        )
    """)
    conn.commit()
    conn.close()

def register_user(user_id: int, username: str, first_name: str):
    conn = sqlite3.connect("ram_vpn.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        cursor.execute(
            "INSERT INTO users (user_id, username, first_name, reg_date) VALUES (?, ?, ?, ?)",
            (user_id, username or "Нет", first_name or "Пользователь", now)
        )
        conn.commit()
    conn.close()

def get_user_info(user_id: int):
    conn = sqlite3.connect("ram_vpn.db")
    cursor = conn.cursor()
    cursor.execute("SELECT reg_date, active_plan FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row if row else (datetime.now().strftime("%d.%m.%Y"), "Не активна")

# ==================== КЛАВИАТУРЫ ====================
def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🚀 Тарифы и подключение", callback_data="tariffs_menu"))
    builder.row(
        types.InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile"),
        types.InlineKeyboardButton(text="🔒 О технологии", callback_data="about")
    )
    builder.row(
        types.InlineKeyboardButton(text="💬 Поддержка", callback_data="support"),
        types.InlineKeyboardButton(text="📑 Документы и Оферта", callback_data="legal")
    )
    return builder.as_markup()

def tariffs_categories_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🛡 RAM Base | Германия (от 149 ₽)", callback_data="cat_base"))
    builder.row(types.InlineKeyboardButton(text="⚡ RAM Pro | 5 стран (от 499 ₽)", callback_data="cat_pro"))
    builder.row(types.InlineKeyboardButton(text="💎 RAM Ultra AI | Gemini + Мощные серверы (7 000 ₽)", callback_data="cat_ultra"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_main"))
    return builder.as_markup()

def category_plans_kb(cat_key: str):
    builder = InlineKeyboardBuilder()
    plans = TARIFFS[cat_key]["plans"]
    for plan_id, info in plans.items():
        btn_text = f"💳 {info['period']} — {info['price']} ₽"
        builder.row(types.InlineKeyboardButton(text=btn_text, callback_data=f"plan_{cat_key}_{plan_id}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ К выбору линейки тарифов", callback_data="tariffs_menu"))
    return builder.as_markup()

def checkout_kb(cat_key: str, plan_id: str):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📲 Оплатить по СБП (QR / Приложение банка)", callback_data=f"pay_sbp_{plan_id}"))
    builder.row(types.InlineKeyboardButton(text="💎 Оплатить Криптовалютой (USDT / TON / BTC)", callback_data=f"pay_crypto_{plan_id}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к тарифу", callback_data=f"cat_{cat_key}"))
    return builder.as_markup()

def back_to_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_main"))
    return builder.as_markup()

# ==================== ТЕКСТЫ ====================
MAIN_TEXT = (
    "⚡️ <b>RAM VPN — Интеллектуальная защита сетевого соединения</b>\n\n"
    "Добро пожаловать в экосистему безопасного интернета. "
    "Мы обеспечиваем криптографическое шифрование трафика, защиту персональных данных "
    "в публичных сетях и стабильную маршрутизацию до мировых облачных и AI-платформ.\n\n"
    "🔹 <b>Стандарты шифрования:</b> 256-bit Enterprise Grade\n"
    "🔹 <b>Инфраструктура:</b> Выделенные дата-центры Tier-3 / Tier-4\n"
    "🔹 <b>Совместимость:</b> iOS, Android, Windows, macOS, Linux\n\n"
    "👇 <i>Выберите нужный раздел в меню ниже:</i>\n"
    "<code>Platega test</code>"
)

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(MAIN_TEXT, reply_markup=main_menu_kb())

@dp.callback_query(F.data == "back_main")
async def cb_back_main(callback: types.CallbackQuery):
    await callback.message.edit_text(MAIN_TEXT, reply_markup=main_menu_kb())
    await callback.answer()

# --- Раздел: Тарифы (Выбор категории) ---
@dp.callback_query(F.data == "tariffs_menu")
async def cb_tariffs_menu(callback: types.CallbackQuery):
    text = (
        "🚀 <b>Тарифные планы RAM VPN</b>\n\n"
        "Мы разработали 3 линейки подписок под любые задачи — от базовой защиты "
        "на каждый день до выделенных высокопроизводительных серверов для работы с ИИ:\n\n"
        "1️⃣ <b>RAM Base (Германия)</b>\n"
        "   └ 1 месяц: <b>149 ₽</b> | 6 мес: <b>599 ₽</b> | 1 год: <b>1 499 ₽</b>\n\n"
        "2️⃣ <b>RAM Pro (Швеция, Франция, США, Финляндия, Германия)</b>\n"
        "   └ 1 месяц: <b>499 ₽</b> | 6 мес: <b>1 999 ₽</b> | 1 год: <b>3 999 ₽</b>\n\n"
        "3️⃣ <b>RAM Ultra AI (Мощные серверы + поддержка Gemini и AI)</b>\n"
        "   └ 1 год: <b>7 000 ₽</b>\n\n"
        "👇 <i>Нажмите на интересующую категорию для просмотра деталей и оформления:</i>"
    )
    await callback.message.edit_text(text, reply_markup=tariffs_categories_kb())
    await callback.answer()

# --- Раздел: Конкретная категория ---
@dp.callback_query(F.data.startswith("cat_"))
async def cb_category_detail(callback: types.CallbackQuery):
    cat_key = callback.data.split("_")[1]
    cat_data = TARIFFS[cat_key]
    
    text = (
        f"{cat_data['title']}\n\n"
        f"🌍 <b>Доступные регионы:</b> {cat_data['locations']}\n\n"
        f"📋 <b>Преимущества тарифа:</b>\n"
        f"{cat_data['features']}\n\n"
        "👇 <i>Выберите период подписки для перехода к оплате:</i>"
    )
    await callback.message.edit_text(text, reply_markup=category_plans_kb(cat_key))
    await callback.answer()

# --- Раздел: Карточка оформления заказа (Checkout) ---
@dp.callback_query(F.data.startswith("plan_"))
async def cb_plan_checkout(callback: types.CallbackQuery):
    _, cat_key, plan_key_part1, plan_key_part2 = callback.data.split("_")
    plan_id = f"{plan_key_part1}_{plan_key_part2}"
    
    cat_data = TARIFFS[cat_key]
    plan_data = cat_data["plans"][plan_id]
    
    text = (
        "🧾 <b>Оформление заказа</b>\n\n"
        f"📦 <b>Тариф:</b> {cat_data['title']}\n"
        f"🌍 <b>Локации:</b> {cat_data['locations']}\n"
        f"⏳ <b>Срок действия:</b> {plan_data['period']}\n"
        f"💰 <b>Итоговая стоимость к оплате:</b> <b>{plan_data['price']} ₽</b>\n\n"
        "🔑 <i>После оплаты вы моментально получите индивидуальный ключ шифрования "
        "и пошаговую инструкцию по подключению в этом боте.</i>\n\n"
        "Оплачивая подписку, вы соглашаетесь с условиями Пользовательского соглашения и Политики конфиденциальности.\n\n"
        "👇 <i>Выберите удобный способ оплаты:</i>"
    )
    await callback.message.edit_text(text, reply_markup=checkout_kb(cat_key, plan_id))
    await callback.answer()

# --- Раздел: Заглушка оплаты (на время проверки Platega) ---
@dp.callback_query(F.data.startswith("pay_"))
async def cb_payment_stub(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    method = "СБП НСПК (QR / Банковское приложение)" if parts[1] == "sbp" else "Криптовалюта (USDT / TON / BTC)"
    plan_id = f"{parts[2]}_{parts[3]}"
    
    price = 0
    title = ""
    for c_key, c_val in TARIFFS.items():
        if plan_id in c_val["plans"]:
            price = c_val["plans"][plan_id]["price"]
            period = c_val["plans"][plan_id]["period"]
            title = f"{c_val['title']} ({period})"
            break

    text = (
        "⏳ <b>Платежный шлюз проходит финальную верификацию</b>\n\n"
        f"🔹 <b>Выбранная услуга:</b> {title}\n"
        f"🔹 <b>Сумма к оплате:</b> {price} ₽\n"
        f"🔹 <b>Способ оплаты:</b> {method}\n"
        f"🔹 <b>Статус терминала:</b> Подключение онлайн-кассы (<code>Platega test</code>)\n\n"
        "В данный момент автоматический прием платежей находится на стадии согласования с банком. "
        "Для ручной активации тарифа или по любым вопросам вы можете написать нашему менеджеру: "
        f"{SUPPORT_TG}"
    )
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨‍💻 Написать менеджеру", url=f"https://t.me/{SUPPORT_TG.replace('@', '')}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Вернуться к тарифам", callback_data="tariffs_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer("Платежный модуль на модерации", show_alert=False)

# --- Раздел: Личный кабинет ---
@dp.callback_query(F.data == "profile")
async def cb_profile(callback: types.CallbackQuery):
    reg_date, active_plan = get_user_info(callback.from_user.id)
    text = (
        "👤 <b>Личный кабинет пользователя</b>\n\n"
        f"🆔 <b>Ваш Telegram ID:</b> <code>{callback.from_user.id}</code>\n"
        f"📅 <b>Дата регистрации:</b> {reg_date}\n"
        f"🛡 <b>Текущая подписка:</b> {active_plan}\n"
        "🔑 <b>Активные ключи:</b> 0 шт.\n\n"
        "<i>Для получения защищенного канала связи выберите подходящий тариф в разделе «Тарифы и подключение».</i>"
    )
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🚀 Выбрать тариф", callback_data="tariffs_menu"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_main"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# --- Раздел: О технологии ---
@dp.callback_query(F.data == "about")
async def cb_about(callback: types.CallbackQuery):
    text = (
        "🔒 <b>О технологии безопасности RAM VPN</b>\n\n"
        "<b>RAM VPN</b> — это специализированный сервис защиты сетевого трафика и обеспечения "
        "конфиденциальности при работе в сети Интернет.\n\n"
        "<b>Для чего используется наш сервис:</b>\n"
        "• <b>Защита в публичных Wi-Fi сетях:</b> предотвращение перехвата паролей и банковских данных в кафе, аэропортах и отелях.\n"
        "• <b>Оптимизация маршрутизации:</b> прямое соединение с европейскими и американскими дата-центрами для снижения пинга.\n"
        "• <b>Работа с облачными и AI-сервисами:</b> тариф <b>RAM Ultra AI</b> обеспечивает стабильную работу с платформой Google Gemini и профессиональными облачными инструментами.\n"
        "• <b>Безопасность:</b> защита от сетевых атак типа MITM (Man-in-the-Middle) и DDoS.\n\n"
        "Владелец проекта: <b>Администрация сервиса «RAM VPN»</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_main_kb())
    await callback.answer()

# --- Раздел: Поддержка ---
@dp.callback_query(F.data == "support")
async def cb_support(callback: types.CallbackQuery):
    text = (
        "💬 <b>Служба заботы и технической поддержки</b>\n\n"
        "Если у вас возникли вопросы по настройке подключения, выбору тарифа или "
        "оплате услуг, наши специалисты готовы помочь:\n\n"
        f"👤 <b>Менеджер в Telegram:</b> {SUPPORT_TG}\n"
        f"📧 <b>Электронная почта:</b> <code>{SUPPORT_EMAIL}</code>\n"
        "🕒 <b>Время работы:</b> Ежедневно, 24/7\n\n"
        "<i>Среднее время ответа в Telegram составляет 5–15 минут.</i>"
    )
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✉️ Написать в поддержку", url=f"https://t.me/{SUPPORT_TG.replace('@', '')}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_main"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# --- Раздел: Документы и Оферта (Единственное место с кнопками документов) ---
@dp.callback_query(F.data == "legal")
async def cb_legal(callback: types.CallbackQuery):
    text = (
        "📑 <b>Правовая информация и документация</b>\n\n"
        f"<b>Владелец сервиса:</b> Администрация сервиса «RAM VPN»\n"
        f"<b>Дата актуальной редакции:</b> {EFFECTIVE_DATE}\n"
        f"<b>Контакты для обращений:</b> {SUPPORT_TG} | {SUPPORT_EMAIL}\n\n"
        "Сервис предоставляет услуги информационной безопасности и шифрования канала связи. "
        "Использование сервиса для любых противоправных действий строго запрещено.\n\n"
        "Постоянные ссылки на полные версии документов доступны по кнопкам ниже:\n"
        f"• <a href='{PRIVACY_URL}'>Политика конфиденциальности (8 разделов)</a>\n"
        f"• <a href='{TERMS_URL}'>Пользовательское соглашение (10 разделов)</a>\n\n"
        "Код проверки для платежного агрегатора: <code>Platega test</code>"
    )
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📄 Политика конфиденциальности", url=PRIVACY_URL))
    builder.row(types.InlineKeyboardButton(text="📋 Пользовательское соглашение", url=TERMS_URL))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_main"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    await callback.answer()

# ==================== ФЕЙКОВЫЙ HTTP-СЕРВЕР ДЛЯ INQUIR ====================
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 3000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ==================== ЗАПУСК ====================
async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    await start_web_server()
    print("✅ База данных и HTTP-сервер инициализированы. Бот RAM VPN запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
