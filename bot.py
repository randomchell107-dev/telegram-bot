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
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from telegram.error import Forbidden

# =========================
# НАСТРОЙКИ
# =========================
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_PASSWORD = "1038362"
CHANNEL_ID = "@popochkashop"

TRUSTED_USERS = ["@popochka17", "@Kirik_o0"]

# Состояния автомата
PASSWORD, MENU, PHOTO, TITLE, DESCRIPTION, PRICE, SIZE, LEGIT, KUFAR, FINAL_MENU, EDIT_CHOICE, EDIT_FIELD = range(12)

# Справочник размеров
SIZES = {
    "XS": "140см",
    "S": "150см",
    "M": "160см",
    "L": "170см",
    "XL": "180см"
}

# КЛАВИАТУРЫ
size_keyboard = [["XS", "S", "M", "L", "XL"]]
legit_keyboard = [["✅ Легит", "❌ Паль"]]
final_keyboard = [["Да", "Редактировать"], ["Отмена"]]
edit_menu_keyboard = [
    ["Фото", "Заголовок", "Описание"],
    ["Цена", "Размер", "Легит"],
    ["Куфар"]
]

user_posts = {}

def build_caption(data):
    return (
        f"<b><i>{data.get('title', 'Без заголовка')}</i></b>\n\n"
        f"<blockquote>{data.get('description', 'Без описания')}</blockquote>\n\n"
        f"<b>🔍 Проверка:</b> {data.get('legit', 'Не указано')}\n"
        f"<b>💰 Цена:</b> {data.get('price', 'Не указана')}\n"
        f"<b>📏 Размер:</b> {data.get('size', 'Не указан')}\n\n"
        f"✍️ <b>Писать ➡️</b> {data.get('kufar_link', 'Нет ссылки')}"
    )

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, data, text_prefix=""):
    chat_id = update.effective_chat.id
    caption = build_caption(data)
    data["caption"] = caption
    
    text_msg = f"{text_prefix}{caption}\n\nВы подтверждаете отправку?"
    
    if len(data.get("photos", [])) > 1:
        media = [InputMediaPhoto(media=img) for img in data["photos"]]
        media[0].caption = text_msg
        media[0].parse_mode = ParseMode.HTML
        await context.bot.send_media_group(chat_id=chat_id, media=media)
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Выберите действие:", 
            reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True)
        )
    else:
        photo = data["photos"][0] if data.get("photos") else "AgACAgIAAxkBAAMZ..."
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=text_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup(final_keyboard, resize_keyboard=True)
        )

# =========================
#ЛОГИКА СТАРТА И ОПРОСА
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте, предъявите пароль администратора пожалуйста.",
        reply_markup=ReplyKeyboardRemove()
    )
    return PASSWORD

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    username = "@" + update.effective_user.username if update.effective_user.username else ""
    
    if username in TRUSTED_USERS or text == ADMIN_PASSWORD:
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=update.effective_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                await update.message.reply_text(f"Для использования бота подпишитесь на канал {CHANNEL_ID}")
                return PASSWORD
        except Forbidden:
            await update.message.reply_text("Добавьте бота в канал администратором.")
            return PASSWORD

        await update.message.reply_text(
            "Доступ подтверждён✅", 
            reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True)
        )
        return MENU
    else:
        await update.message.reply_text("Пароль неверный!")
        return PASSWORD

async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_posts[user_id] = {"photos": []}
    await update.message.reply_text(
        "Заполните пост пожалуйста.\n\nШаг 1: Отправьте ОДНУ фотографию товара:",
        reply_markup=ReplyKeyboardRemove()
    )
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте именно картинку.")
        return PHOTO
        
    photo_id = update.message.photo[-1].file_id
    user_posts[user_id]["photos"] = [photo_id]
    
    await update.message.reply_text("Фото успешно добавлено📸\n\nШаг 2: Введите главный заголовок вещи.")
    return TITLE

async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_posts[user_id]["title"] = update.message.text.strip()
    await update.message.reply_text("Шаг 3: Введите описание вещи.")
    return DESCRIPTION

async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_posts[user_id]["description"] = update.message.text.strip()
    await update.message.reply_text("Шаг 4: Введите цену.")
    return PRICE

async def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if "BYN" not in text.upper():
        text = text + " BYN"
    user_posts[user_id]["price"] = text
    await update.message.reply_text(
        "Шаг 5: Выберите размер вещи:", 
        reply_markup=ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True)
    )
    return SIZE

async def handle_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()
    user_posts[user_id]["size"] = f"{text} ({SIZES[text]})" if text in SIZES else text
    await update.message.reply_text(
        "Шаг 6: Легит? (Выберите на кнопках)", 
        reply_markup=ReplyKeyboardMarkup(legit_keyboard, resize_keyboard=True)
    )
    return LEGIT

async def handle_legit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_posts[user_id]["legit"] = update.message.text.strip()
    await update.message.reply_text("Шаг 7: Впишите ссылку на Куфар.", reply_markup=ReplyKeyboardRemove())
    return KUFAR

async def handle_kufar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.text:
        return KUFAR
        
    user_posts[user_id]["kufar_link"] = update.message.text.strip()
    await show_preview(update, context, user_posts[user_id], text_prefix="Вот так будет выглядеть готовый пост:\n\n")
    return FINAL_MENU

# =========================
# УПРАВЛЕНИЕ ПУБЛИКАЦИЕЙ
# =========================
async def handle_final_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = update.message.text.strip().lower()
    data = user_posts.get(user_id)
    
    if action == "да":
        if len(data.get("photos", [])) > 1:
            media = [InputMediaPhoto(media=img) for img in data["photos"]]
            media[0].caption = data["caption"]
            media[0].parse_mode = ParseMode.HTML
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        else:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=data["photos"][0], 
                caption=data["caption"], parse_mode=ParseMode.HTML
            )
        await update.message.reply_text(
            "Пост отправлен в канал!✅", 
            reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True)
        )
        return MENU
        
    elif action == "редактировать":
        await update.message.reply_text(
            "Что нужно изменить?", 
            reply_markup=ReplyKeyboardMarkup(edit_menu_keyboard, resize_keyboard=True)
        )
        return EDIT_CHOICE
        
    elif action == "отмена":
        await update.message.reply_text(
            "Создание поста отменено.", 
            reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True)
        )
        return MENU
    else:
        await update.message.reply_text("Используйте кнопки: Да, Редактировать или Отмена.")
        return FINAL_MENU

async def handle_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    fields_map = {
        "фото": "photos", "заголовок": "title", "описание": "description",
        "цена": "price", "размер": "size", "легит": "legit", "куфар": "kufar_link"
    }
    
    if text in fields_map:
        context.user_data["edit_field"] = fields_map[text]
        if text == "фото":
            await update.message.reply_text("Отправьте новую фотографию товара:", reply_markup=ReplyKeyboardRemove())
        elif text == "размер":
            await update.message.reply_text("Выберите новый размер:", reply_markup=ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True))
        elif text == "легит":
            await update.message.reply_text("Выберите статус проверки:", reply_markup=ReplyKeyboardMarkup(legit_keyboard, resize_keyboard=True))
        else:
            await update.message.reply_text(f"Введите новое значение для поля [{text}]:", reply_markup=ReplyKeyboardRemove())
        return EDIT_FIELD
    else:
        await update.message.reply_text("Выберите пункт на клавиатуре.", reply_markup=ReplyKeyboardMarkup(edit_menu_keyboard, resize_keyboard=True))
        return EDIT_CHOICE

async def handle_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    field = context.user_data.get("edit_field")
    
    if field == "photos":
        if not update.message.photo:
            await update.message.reply_text("Пожалуйста, отправьте фото.")
            return EDIT_FIELD
        user_posts[user_id]["photos"] = [update.message.photo[-1].file_id]
    else:
        text = update.message.text.strip()
        if field == "price" and "BYN" not in text.upper():
            text = text + " BYN"
        elif field == "size":
            text = f"{text.upper()} ({SIZES[text.upper()]})" if text.upper() in SIZES else text
        user_posts[user_id][field] = text

    await show_preview(update, context, user_posts[user_id], text_prefix="Пункт успешно изменен! Новый вариант:\n\n")
    return FINAL_MENU

# =========================================================
# СЕРВЕР RENDER PING
# =========================================================
async def handle_render_ping(reader, writer):
    try:
        await reader.read(100)
        response = "HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nHello Render"
        writer.write(response.encode())
        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()

async def start_ping_server():
    port = int(os.environ.get("PORT", 10000))
    server = await asyncio.start_server(handle_render_ping, '0.0.0.0', port)
    async with server:
        await server.serve_forever()

# =========================================================
# ЗАПУСК
# =========================================================
async def main():
    if not TOKEN:
        print("Ошибка: BOT_TOKEN не задан!")
        return

    app = Application.builder().token(TOKEN).build()

    # Изолированный фильтр приватных сообщений без команд
    msg_filter = filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PASSWORD: [MessageHandler(msg_filter, handle_password)],
            MENU: [MessageHandler(filters.ChatType.PRIVATE & filters.Text(["пост", "Пост"]), start_post)],
            PHOTO: [MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo)],
            TITLE: [MessageHandler(msg_filter, handle_title)],
            DESCRIPTION: [MessageHandler(msg_filter, handle_description)],
            PRICE: [MessageHandler(msg_filter, handle_price)],
            SIZE: [MessageHandler(msg_filter, handle_size)],
            LEGIT: [MessageHandler(msg_filter, handle_legit)],
            KUFAR: [MessageHandler(filters.ChatType.PRIVATE & (filters.TEXT | filters.StatusUpdate) & ~filters.COMMAND, handle_kufar)],
            FINAL_MENU: [MessageHandler(msg_filter, handle_final_menu)],
            EDIT_CHOICE: [MessageHandler(msg_filter, handle_edit_choice)],
            EDIT_FIELD: [
                MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_edit_field),
                MessageHandler(msg_filter, handle_edit_field)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)

    await app.initialize()
    await app.start()

    await asyncio.gather(
        app.updater.start_polling(allowed_updates=Update.ALL_TYPES),
        start_ping_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
