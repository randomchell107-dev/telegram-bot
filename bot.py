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

TRUSTED_USERS = [
    "@popochka17",
    "@Kirik_o0"
]

# =========================
# СОСТОЯНИЯ И ПАМЯТЬ
# =========================
authorized_users = {}
post_data = {}

# Глобальные хранилища для сборки альбомов
album_buffers = {}
album_tasks = {}

# =========================
# КЛАВИАТУРЫ
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
# НАКОПИТЕЛЬ ФОТОГРАФИЙ
# =========================
async def trigger_album_collected(user_id, context: ContextTypes.DEFAULT_TYPE, chat_id, is_editing=False):
    await asyncio.sleep(1.5)  # Оптимальное время ожидания пачки фото
    
    photos = album_buffers.get(user_id, []).copy()
    album_buffers[user_id] = []
    
    if user_id in album_tasks:
        del album_tasks[user_id]
        
    if not photos:
        return

    if is_editing:
        post_data[user_id]["photos"] = photos
        post_data[user_id]["editing_field"] = None
        await show_preview(user_id, context, chat_id, text_prefix="Пост обновлен! Вот новый вариант:\n\n")
    else:
        post_data[user_id]["photos"] = photos
        await context.bot.send_message(
            chat_id=chat_id,
            text="Фото успешно добавлены📸 Всего: " + str(len(photos)) + "\n\nШаг 2: Введите главный заголовок вещи."
        )

# =========================
# ФУНКЦИЯ ВЫВОДА ПРЕДПРОСМОТРА
# =========================
async def show_preview(user_id, context: ContextTypes.DEFAULT_TYPE, chat_id, text_prefix=""):
    data = post_data[user_id]
    caption = build_caption(data)
    post_data[user_id]["caption"] = caption
    
    text_msg = f"{text_prefix}{caption}\n\nВы подтверждаете отправку?"
    
    # Отправка одной фотки или полноценного альбома
    if len(data.get("photos", [])) > 1:
        media = [InputMediaPhoto(media=img) for img in data["photos"]]
        media[0].caption = text_msg
        media[0].parse_mode = ParseMode.HTML
        await context.bot.send_media_group(chat_id=chat_id, media=media)
        # Отдельное сообщение с клавиатурой, так как к медиагруппе её прикрепить нельзя
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Выберите действие ниже на клавиатуре:", 
            reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True)
        )
    else:
        photo_to_send = data["photos"][0] if data.get("photos") else "AgACAgIAAxkBAAMZ..." 
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo_to_send,
            caption=text_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True)
        )

# =========================
# ГЛАВНЫЙ ОБРАБОТЧИК
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return  

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip() if update.message.text else ""

    # Инициализация сессии юзера
    if user_id not in authorized_users:
        authorized_users[user_id] = False
    if user_id not in post_data:
        post_data[user_id] = {}

    username = "@" + update.effective_user.username if update.effective_user.username else ""

    # ПРОВЕРКА ПОДПИСКИ
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"Для использования бота подпишитесь на канал {CHANNEL_ID}")
            return
    except Forbidden:
        await update.message.reply_text("Добавьте бота в канал администратором для проверки подписки.")
        return

    # ПРОВЕРКА АВТОРИЗАЦИИ
    if not authorized_users[user_id]:
        if username in TRUSTED_USERS or text == ADMIN_PASSWORD:
            authorized_users[user_id] = True
            await update.message.reply_text(
                "Доступ подтверждён✅", 
                reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("Пароль неверный!")
        return

    # Глобальный сброс по команде "пост"
    if text.lower() == "пост":
        post_data[user_id] = {"creating_post": True}
        album_buffers[user_id] = []
        if user_id in album_tasks:
            album_tasks[user_id].cancel()
            del album_tasks[user_id]
        await update.message.reply_text(
            "Заполните пост пожалуйста.\n\nШаг 1: Отправьте фото товара (можно сразу несколько).",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # =====================================================
    # 1. РЕЖИМ ИЗМЕНЕНИЯ ВЫБРАННОГО ПОЛЯ
    # =====================================================
    if post_data[user_id].get("editing_field"):
        field = post_data[user_id]["editing_field"]
        
        if field == "photo":
            if update.message.photo:
                if user_id not in album_buffers:
                    album_buffers[user_id] = []
                album_buffers[user_id].append(update.message.photo[-1].file_id)
                
                if user_id not in album_tasks:
                    album_tasks[user_id] = asyncio.create_task(
                        trigger_album_collected(user_id, context, chat_id, is_editing=True)
                    )
                return
            else:
                await update.message.reply_text("Пожалуйста, отправьте фото.")
                return
        else:
            if not text:
                await update.message.reply_text("Пожалуйста, отправьте текстовое значение.")
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
            await show_preview(user_id, context, chat_id, text_prefix="Пост обновлен! Вот новый вариант:\n\n")
            return

    # =====================================================
    # 2. РЕЖИМ ВЫБОРА ПОЛЯ ДЛЯ РЕДАКТИРОВАНИЯ
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
                await update.message.reply_text("Выберите новый размер вещи на кнопках:", reply_markup=ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True))
            elif chosen == "легит":
                await update.message.reply_text("Выберите новый статус легита вещи на кнопках:", reply_markup=ReplyKeyboardMarkup(legit_keyboard, resize_keyboard=True))
            elif chosen == "фото":
                album_buffers[user_id] = []
                await update.message.reply_text("Отправьте новое фото или пачку фотографий:", reply_markup=ReplyKeyboardRemove())
            else:
                await update.message.reply_text(f"Введите новое значение для поля [{chosen}]:", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text("Используйте кнопки на экране для выбора поля.", reply_markup=ReplyKeyboardMarkup(edit_menu_keyboard, resize_keyboard=True))
        return

    # =====================================================
    # 3. ПОШАГОВЫЙ СБОР ДАННЫХ ПОСТА (АНКЕТА)
    # =====================================================
    if post_data[user_id].get("creating_post"):
        
        # Шаг 1: Фотографии вещи
        if "photos" not in post_data[user_id]:
            if update.message.photo:
                if user_id not in album_buffers:
                    album_buffers[user_id] = []
                album_buffers[user_id].append(update.message.photo[-1].file_id)
                
                if user_id not in album_tasks:
                    album_tasks[user_id] = asyncio.create_task(
                        trigger_album_collected(user_id, context, chat_id, is_editing=False)
                    )
                return
            else:
                await update.message.reply_text("Пожалуйста, отправьте фотографии товара для Шага 1.")
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

        # Шаг 6: Легит (✅ или ❌)
        if "legit" not in post_data[user_id]:
            if text:
                post_data[user_id]["legit"] = text
                await update.message.reply_text("Шаг 7: Впишите ссылку на Куфар.", reply_markup=ReplyKeyboardRemove())
            return

        # Шаг 7: Ссылка Куфар -> Показ финального меню
        if "kufar_link" not in post_data[user_id]:
            if text:
                post_data[user_id]["kufar_link"] = text
                post_data[user_id]["creating_post"] = False  # Анкета успешно завершена
                await show_preview(user_id, context, chat_id, text_prefix="Вот так будет выглядеть готовый пост:\n\n")
            return

    # =====================================================
    # 4. ФИНАЛЬНОЕ МЕНЮ ПОДТВЕРЖДЕНИЯ (Да / Редактировать / Отмена)
    # =====================================================
    chosen_action = text.lower()
    
    if chosen_action == "да":
        data = post_data[user_id]
        if not data.get("photos"):
            await update.message.reply_text("Ошибка: фотографии поста утеряны. Нажмите «пост» заново.")
            return

        # Публикация альбома или одиночного фото
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
            
        await update.message.reply_text(
            "Пост был успешно отправлен в канал✅", 
            reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True)
        )
        post_data[user_id] = {}

    elif chosen_action == "редактировать":
        post_data[user_id]["waiting_for_edit_choice"] = True
        await update.message.reply_text(
            "Выберите пункт для изменения:", 
            reply_markup=ReplyKeyboardMarkup(edit_menu_keyboard, resize_keyboard=True)
        )

    elif chosen_action in ["отмена", "нет"]:
        post_data[user_id] = {}
        await update.message.reply_text(
            "Создание поста отменено.", 
            reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True)
        )
        
    else:
        # Если заполнение завершено, но юзер пишет обычный текст вместо кликов по кнопкам меню
        if "photos" in post_data[user_id]:
            await update.message.reply_text(
                "Пожалуйста, используйте кнопки управления: Да, Редактировать или Отмена.",
                reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                "Для создания публикации нажмите кнопку «пост».", 
                reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True)
            )

# =========================================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER PING
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
# ЗАПУСК
# =========================================================
async def main():
    if not TOKEN:
        print("Ошибка: BOT_TOKEN не найден в переменных окружения!")
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
