import os
import asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InputMediaPhoto
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
# ПАМЯТЬ БОТА
# =========================
authorized_users = {}
post_data = {}
media_groups = {}  # Буфер для сборки альбомов из фото

# =========================
# КЛАВИАТУРЫ И СЛОВАРИ
# =========================
sizes = {
    "XS": "140см",
    "S": "150см",
    "M": "160см",
    "L": "170см",
    "XL": "180см"
}
size_keyboard = [["XS", "S", "M", "L", "XL"]]
legit_keyboard = [["✅ Легит", "❌ Паль"]]
final_keyboard = [["Да", "Редактировать"], ["Отмена"]]
edit_menu_keyboard = [
    ["Фото", "Заголовок", "Описание"],
    ["Цена", "Размер", "Легит"],
    ["Куфар"]
]

# =========================
# ФУНКЦИЯ СБОРКИ ТЕКСТА
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
# ОБРАБОТКА МНОЖЕСТВА ФОТО (АЛЬБОМ)
# =========================
async def process_photos_buffer(user_id, context: ContextTypes.DEFAULT_TYPE, chat_id):
    await asyncio.sleep(1.0)  # Ждем 1 секунду, пока прилетят все фото пачки
    if user_id in media_groups and media_groups[user_id]:
        post_data[user_id]["photos"] = media_groups[user_id].copy()
        media_groups[user_id] = []
        await context.bot.send_message(
            chat_id=chat_id,
            text="Фото успешно добавлены📸\n\nШаг 2: Введите главный заголовок вещи."
        )

# =========================
# ГЛАВНЫЙ ОБРАБОТЧИК
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return  

    user_id = update.effective_user.id
    text = update.message.text if update.message.text else ""
    chat_id = update.effective_chat.id

    if user_id not in authorized_users:
        authorized_users[user_id] = False
    if user_id not in post_data:
        post_data[user_id] = {}

    username = "@" + update.effective_user.username if update.effective_user.username else ""

    # 1. ПРОВЕРКА ПОДПИСКИ
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"Для использования бота подпишитесь на канал {CHANNEL_ID}")
            return
    except Forbidden:
        await update.message.reply_text("Бот не может проверить подписку. Добавьте бота в канал администратором.")
        return

    # 2. ПРОВЕРКА ПАРОЛЯ
    if not authorized_users[user_id]:
        if username in TRUSTED_USERS or text == ADMIN_PASSWORD:
            authorized_users[user_id] = True
            keyboard = [["пост"]]
            await update.message.reply_text("Доступ подтверждён✅", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        else:
            await update.message.reply_text("Пароль неверный!")
        return

    # =====================================================
    # РЕЖИМ ОДИНОЧНОГО РЕДАКТИРОВАНИЯ ПОЛЯ
    # =====================================================
    if post_data[user_id].get("editing_field"):
        field = post_data[user_id]["editing_field"]
        
        if field == "photo":
            if update.message.photo:
                # Если прислали пачку фото при редактировании
                if user_id not in media_groups:
                    media_groups[user_id] = []
                media_groups[user_id].append(update.message.photo[-1].file_id)
                
                # Запускаем таймер сборки
                asyncio.create_task(asyncio.sleep(1.0))
                await asyncio.sleep(1.1)
                
                if media_groups[user_id]:
                    post_data[user_id]["photos"] = media_groups[user_id].copy()
                    media_groups[user_id] = []
                
                post_data[user_id]["editing_field"] = None
            else:
                await update.message.reply_text("Пожалуйста, отправьте фото.")
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
                post_data[user_id]["size"] = f"{size_input} ({sizes[size_input]})" if size_input in sizes else size_input
            elif field == "legit":
                post_data[user_id]["legit"] = text
            elif field == "kufar_link":
                post_data[user_id]["kufar_link"] = text
            
            post_data[user_id]["editing_field"] = None

        # Выводим обновленный предпросмотр
        caption = build_caption(post_data[user_id])
        post_data[user_id]["caption"] = caption
        
        # Отправляем предпросмотр (одно фото или альбом)
        if len(post_data[user_id].get("photos", [])) > 1:
            media = [InputMediaPhoto(media=img) for img in post_data[user_id]["photos"]]
            media[0].caption = f"Пост обновлен! Вот новый вариант:\n\n{caption}\n\nВы подтверждаете отправку?"
            media[0].parse_mode = ParseMode.HTML
            await context.bot.send_media_group(chat_id=chat_id, media=media)
            await context.bot.send_message(chat_id=chat_id, text="Подтверждаете?", reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True))
        else:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=post_data[user_id]["photos"][0],
                caption=f"Пост обновлен! Вот новый вариант:\n\n{caption}\n\nВы подтверждаете отправку?",
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True)
            )
        return

    # =====================================================
    # ВЫБОР ПОЛЯ ДЛЯ РЕДАКТИРОВАНИЯ
    # =====================================================
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
                await update.message.reply_text("Выберите новый размер:", reply_markup=ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True))
            elif chosen == "легит":
                await update.message.reply_text("Выберите статус легита:", reply_markup=ReplyKeyboardMarkup(legit_keyboard, resize_keyboard=True))
            elif chosen == "фото":
                await update.message.reply_text("Отправьте новое фото или несколько фото товара:", reply_markup=ReplyKeyboardRemove())
            else:
                await update.message.reply_text(f"Введите новое значение для поля [{chosen}]:", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text("Выберите поле с помощью кнопок.")
        return

    # =====================================================
    # СТАРТ СОЗДАНИЯ ПОСТА
    # =====================================================
    if not post_data[user_id] or text.lower() == "пост":
        if text.lower() == "пост":
            post_data[user_id] = {"creating_post": True}
            media_groups[user_id] = []
            await update.message.reply_text(
                "Заполните пост пожалуйста.\n\nШаг 1: Отправьте фото товара (можно сразу несколько!).",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("Нажмите кнопку «пост».", reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True))
        return

    # =====================================================
    # ПОШАГОВЫЙ БЛАНКПОСТИНГ
    # =====================================================
    # Шаг 1: Сбор фоток (работает как для одной, так и для пачки)
    if "photos" not in post_data[user_id]:
        if update.message.photo:
            if user_id not in media_groups:
                media_groups[user_id] = []
            
            media_groups[user_id].append(update.message.photo[-1].file_id)
            
            # Если это первое фото в пакете, запускаем сборщик таймаута
            if len(media_groups[user_id]) == 1:
                asyncio.create_task(process_photos_buffer(user_id, context, chat_id))
            return
        else:
            await update.message.reply_text("Пожалуйста, отправьте фото товара.")
            return

    # Шаг 2: Заголовок
    if "title" not in post_data[user_id]:
        if text:
            post_data[user_id]["title"] = text
            await update.message.reply_text("Шаг 3: Введите описание вещи.")
        return

    # Шаг 3: Описание
    if "description" not in post_data[user_id]:
        if text:
            post_data[user_id]["description"] = text
            await update.message.reply_text("Шаг 4: Введите цену.")
        return

    # Шаг 4: Цена
    if "price" not in post_data[user_id]:
        if text:
            if "BYN" not in text.upper():
                text = text + " BYN"
            post_data[user_id]["price"] = text
            await update.message.reply_text("Шаг 5: Выберите размер вещи.", reply_markup=ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True))
        return

    # Шаг 5: Размер
    if "size" not in post_data[user_id]:
        if text:
            size_input = text.upper()
            post_data[user_id]["size"] = f"{size_input} ({sizes[size_input]})" if size_input in sizes else size_input
            await update.message.reply_text("Шаг 6: Легит? (Выберите кнопку ✅ или ❌)", reply_markup=ReplyKeyboardMarkup(legit_keyboard, resize_keyboard=True))
        return

    # Шаг 6: Легит (Кнопки ✅ / ❌)
    if "legit" not in post_data[user_id]:
        if text:
            post_data[user_id]["legit"] = text
            await update.message.reply_text("Шаг 7: Впишите ссылку на Куфар.", reply_markup=ReplyKeyboardRemove())
        return

    # Шаг 7: Ссылка на Куфар -> Финальный предпросмотр
    if "kufar_link" not in post_data[user_id]:
        if text:
            post_data[user_id]["kufar_link"] = text
            caption = build_caption(post_data[user_id])
            post_data[user_id]["caption"] = caption

            # Отправляем предпросмотр
            if len(post_data[user_id]["photos"]) > 1:
                media = [InputMediaPhoto(media=img) for img in post_data[user_id]["photos"]]
                media[0].caption = f"Вот так будет выглядеть готовый пост:\n\n{caption}\n\nВы подтверждаете отправку?"
                media[0].parse_mode = ParseMode.HTML
                await context.bot.send_media_group(chat_id=chat_id, media=media)
                await context.bot.send_message(chat_id=chat_id, text="Выберите действие:", reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True))
            else:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=post_data[user_id]["photos"][0],
                    caption=f"Вот так будет выглядеть готовый пост:\n\n{caption}\n\nВы подтверждаете отправку?",
                    parse_mode=ParseMode.HTML,
                    reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True)
                )
        return

    # =====================================================
    # ФИНАЛЬНЫЙ ВЫБОР АДМИНА (Да / Редактировать / Отмена)
    # =====================================================
    chosen_action = text.lower()
    
    if chosen_action == "да":
        data = post_data[user_id]
        
        # Публикация в канал альбомом или одной фоткой
        if len(data["photos"]) > 1:
            media = [InputMediaPhoto(media=img) for img in data["photos"]]
            media[0].caption = data["caption"]
            media[0].parse_mode = ParseMode.HTML
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        else:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=data["photos"][0],
                caption=data["caption"],
                parse_mode=ParseMode.HTML
            )
            
        await update.message.reply_text("Пост был успешно отправлен в канал✅", reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True))
        post_data[user_id] = {}

    elif chosen_action == "редактировать":
        post_data[user_id]["waiting_for_edit_choice"] = True
        await update.message.reply_text("Выберите, какой пункт вы хотите изменить:", reply_markup=ReplyKeyboardMarkup(edit_menu_keyboard, resize_keyboard=True))

    elif chosen_action in ["отмена", "нет"]:
        post_data[user_id] = {}
        await update.message.reply_text("Создание поста отменено.", reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True))
        
    else:
        # Если юзер ввел левый текст вместо нажатия кнопок Да/Редактировать
        await update.message.reply_text("Пожалуйста, используйте кнопки на клавиатуре: Да, Редактировать или Отмена.")

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
        print("Ошибка: Токен бота не найден!")
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
