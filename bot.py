import os
import asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
)
from telegram.error import Forbidden

# =========================
# НАСТРОЙКИ
# =========================
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_PASSWORD = "1038362"
CHANNEL_ID = "@popochkashop"

# =========================
# БЕЗ ПАРОЛЯ
# =========================
TRUSTED_USERS = [
    "@popochka17",
    "@Kirik_o0"
]

# =========================
# ПАМЯТЬ
# =========================
authorized_users = {}
post_data = {}

# =========================
# РАЗМЕРЫ И КЛАВИАТУРА
# =========================
sizes = {
    "XS": "140см",
    "S": "150см",
    "M": "160см",
    "L": "170см",
    "XL": "180см"
}
# Быстрые кнопки для размеров
size_keyboard = [["XS", "S", "M", "L", "XL"]]

# =========================
# ФУНКЦИЯ СБОРКИ ТЕКСТА ПОСТА
# =========================
def build_caption(data):
    return (
        f"<b><i>{data.get('title', 'Без заголовка')}</i></b>\n\n"
        f"<blockquote>{data.get('description', 'Без описания')}</blockquote>\n\n"
        f"<b>🔍 Проверка:</b> {data.get('legit', 'Не указано')}\n"
        f"<b>💰 Цена:</b> {data.get('price', 'Не указана')}\n"
        f"<b>📏 Размер:</b> {data.get('size', 'Не указан')}\n\n"
        f"✍️ <b>Писать ➡️</b> {data.get('kufar_link', 'Нет ссылки')}"
    )

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    authorized_users[user_id] = False
    post_data[user_id] = {}

    await update.message.reply_text(
        "Здравствуйте, предъявите пароль администратора пожалуйста.",
        reply_markup=ReplyKeyboardRemove()
    )

# =========================
# ОБРАБОТКА
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Защита от пустых апдейтов и сообщений из каналов
    if not update.message or not update.effective_user:
        return  

    user_id = update.effective_user.id
    text = update.message.text if update.message.text else ""

    if user_id not in authorized_users:
        authorized_users[user_id] = False

    if user_id not in post_data:
        post_data[user_id] = {}

    username = ""
    if update.effective_user.username:
        username = "@" + update.effective_user.username

    # =========================
    # ПРОВЕРКА ПОДПИСКИ
    # =========================
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"Для использования бота подпишитесь на канал {CHANNEL_ID}")
            return
    except Forbidden:
        await update.message.reply_text("Бот не может проверить подписку. Добавьте бота в канал администратором.")
        return

    # =========================
    # ПРОВЕРКА ПАРОЛЯ
    # =========================
    if not authorized_users[user_id]:
        if username in TRUSTED_USERS or text == ADMIN_PASSWORD:
            authorized_users[user_id] = True
            keyboard = [["пост"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Доступ подтверждён✅", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Пароль неверный!")
        return

    # =========================
    # РЕЖИМ РЕДАКТИРОВАНИЯ КОНКРЕТНОГО ПУНКТА
    # =========================
    if post_data[user_id].get("editing_field"):
        field = post_data[user_id]["editing_field"]
        
        if field == "photo":
            if update.message.photo:
                post_data[user_id]["photo"] = update.message.photo[-1].file_id
                post_data[user_id]["editing_field"] = None
            else:
                await update.message.reply_text("Пожалуйста, отправьте именно фото.")
                return
        else:
            if not text:
                await update.message.reply_text("Пожалуйста, отправьте текст.")
                return
                
            if field == "title":
                post_data[user_id]["title"] = text
            elif field == "description":
                post_data[user_id]["description"] = text
            elif field == "price":
                if "BYN" not in text.upper():
                    text = text + " BYN"
                post_data[user_id]["price"] = text
            elif field == "size":
                size_input = text.upper()
                if size_input in sizes:
                    post_data[user_id]["size"] = f"{size_input} ({sizes[size_input]})"
                else:
                    post_data[user_id]["size"] = size_input
            elif field == "legit":
                post_data[user_id]["legit"] = text
            elif field == "kufar_link":
                post_data[user_id]["kufar_link"] = text
            
            post_data[user_id]["editing_field"] = None

        # Возвращаем предпросмотр
        caption = build_caption(post_data[user_id])
        post_data[user_id]["caption"] = caption
        keyboard = [["Да", "Редактировать"], ["Отмена"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_photo(
            photo=post_data[user_id]["photo"],
            caption=f"Пост обновлен! Вот новый вариант:\n\n{caption}\n\nВы подтверждаете отправку?",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        return

    # =========================
    # КОНСТРУКТОР: ВЫБОР ЧТО РЕДАКТИРОВАТЬ
    # =========================
    if post_data[user_id].get("waiting_for_edit_choice"):
        fields_map = {
            "фото": "photo", "заголовок": "title", "описание": "description",
            "цена": "price", "размер": "size", "легит": "legit", "куфар": "kufar_link"
        }
        chosen = text.lower()
        if chosen in fields_map:
            post_data[user_id]["editing_field"] = fields_map[chosen]
            post_data[user_id]["waiting_for_edit_choice"] = False
            
            if chosen == "размер":
                reply_markup = ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True)
                await update.message.reply_text("Выберите новый размер на клавиатуре:", reply_markup=reply_markup)
            elif chosen == "легит":
                keyboard = [["Есть", "Любые проверки"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text("Введите новый статус легита или выберите кнопку:", reply_markup=reply_markup)
            elif chosen == "фото":
                await update.message.reply_text("Отправьте новое фото товара:", reply_markup=ReplyKeyboardRemove())
            else:
                await update.message.reply_text(f"Введите новое значение для поля [{chosen}]:", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text("Используйте кнопки на клавиатуре для выбора поля.")
        return

    # =========================
    # СТАРТ СОЗДАНИЯ ПОСТА
    # =========================
    if not post_data[user_id]:
        if text.lower() == "пост":
            post_data[user_id]["creating_post"] = True
            await update.message.reply_text(
                "Заполните пост пожалуйста.\n\nШаг 1: Отправьте фото товара.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            keyboard = [["пост"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Нажмите кнопку «пост».", reply_markup=reply_markup)
        return

    # =========================
    # ПОШАГОВЫЙ БЛАНКПОСТИНГ
    # =========================
    # 1. Фото
    if "photo" not in post_data[user_id]:
        if update.message.photo:
            post_data[user_id]["photo"] = update.message.photo[-1].file_id
            await update.message.reply_text("Шаг 2: Введите главный заголовок вещи.")
        else:
            await update.message.reply_text("Пожалуйста, отправьте фото товара.")
        return

    # 2. Заголовок
    if "title" not in post_data[user_id]:
        if text:
            post_data[user_id]["title"] = text
            await update.message.reply_text("Шаг 3: Введите описание вещи.")
        return

    # 3. Описание
    if "description" not in post_data[user_id]:
        if text:
            post_data[user_id]["description"] = text
            await update.message.reply_text("Шаг 4: Введите цену.")
        return

    # 4. Цена
    if "price" not in post_data[user_id]:
        if text:
            if "BYN" not in text.upper():
                text = text + " BYN"
            post_data[user_id]["price"] = text
            # Показываем кнопки размеров
            reply_markup = ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True)
            await update.message.reply_text("Шаг 5: Выберите размер вещи.", reply_markup=reply_markup)
        return

    # 5. Размер
    if "size" not in post_data[user_id]:
        if text:
            size_input = text.upper()
            if size_input in sizes:
                post_data[user_id]["size"] = f"{size_input} ({sizes[size_input]})"
            else:
                post_data[user_id]["size"] = size_input
            
            # Предлагаем быстрые кнопки для Легита
            keyboard = [["Есть", "Любые проверки"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Шаг 6: Укажите легит (Проверка на оригинал).", reply_markup=reply_markup)
        return

    # 6. Легит
    if "legit" not in post_data[user_id]:
        if text:
            post_data[user_id]["legit"] = text
            await update.message.reply_text("Шаг 7: Впишите свою ссылку на куфар.", reply_markup=ReplyKeyboardRemove())
        return

    # 7. Ссылка Куфар -> Предпросмотр
    if "kufar_link" not in post_data[user_id]:
        if text:
            post_data[user_id]["kufar_link"] = text
            caption = build_caption(post_data[user_id])
            post_data[user_id]["caption"] = caption

            keyboard = [["Да", "Редактировать"], ["Отмена"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_photo(
                photo=post_data[user_id]["photo"],
                caption=f"Вот так будет выглядеть готовый пост:\n\n{caption}\n\nВы подтверждаете отправку?",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        return

    # =========================
    # МЕНЮ ФИНАЛЬНОГО ВЫБОРА
    # =========================
    chosen_action = text.lower()
    
    if chosen_action == "да":
        data = post_data[user_id]
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=data["photo"],
            caption=data["caption"],
            parse_mode=ParseMode.HTML
        )
        keyboard = [["пост"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Пост был успешно отправлен в канал✅", reply_markup=reply_markup)
        post_data[user_id] = {}

    elif chosen_action == "редактировать":
        post_data[user_id]["waiting_for_edit_choice"] = True
        keyboard = [
            ["Фото", "Заголовок", "Описание"],
            ["Цена", "Размер", "Легит"],
            ["Куфар"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите, какой пункт вы хотите изменить:", reply_markup=reply_markup)

    elif chosen_action in ["отмена", "нет"]:
        keyboard = [["пост"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        post_data[user_id] = {}
        await update.message.reply_text("Создание поста отменено.", reply_markup=reply_markup)
        
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки: Да, Редактировать или Отмена.")

# =========================================================
# АСИНХРОННЫЙ СЕРВЕР ДЛЯ RENDER
# =========================================================
async def handle_render_ping(reader, writer):
    try:
        data = await reader.read(100)
        response = "HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello Render"
        writer.write(response.encode())
        await writer.drain()
    except Exception as e:
        print(f"Ошибка сервера пинга: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def start_ping_server():
    port = int(os.environ.get("PORT", 10000))
    server = await asyncio.start_server(handle_render_ping, '0.0.0.0', port)
    print(f"Сервер проверки Render запущен на порту {port}")
    async with server:
        await server.serve_forever()

# =========================================================
# ГЛАВНЫЙ АСИНХРОННЫЙ ЗАПУСК
# =========================================================
async def main():
    if not TOKEN:
        print("Ошибка: Токен бота (BOT_TOKEN) не найден!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    print("Инициализация приложения...")
    await app.initialize()
    await app.start()
    print("Бот полностью готов к работе.")

    await asyncio.gather(
        app.updater.start_polling(allowed_updates=Update.ALL_TYPES),
        start_ping_server()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
