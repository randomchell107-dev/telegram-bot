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
# ПАМЯТЬ БОТА
# =========================
authorized_users = {}
post_data = {}
processed_albums = set()  # Чтобы не обрабатывать один альбом по 10 раз

# Справочник размеров
sizes = {
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
    post_data[user_id] = {"step": "password"}
    await update.message.reply_text(
        "Здравствуйте, предъявите пароль администратора пожалуйста.",
        reply_markup=ReplyKeyboardRemove()
    )

# =========================
# ФУНКЦИЯ ПРЕДПРОСМОТРА
# =========================
async def show_preview(user_id, context: ContextTypes.DEFAULT_TYPE, chat_id, text_prefix=""):
    data = post_data[user_id]
    caption = build_caption(data)
    post_data[user_id]["caption"] = caption
    
    text_msg = f"{text_prefix}{caption}\n\nВы подтверждаете отправку?"
    
    if len(data.get("photos", [])) > 1:
        media = [InputMediaPhoto(media=img) for img in data["photos"]]
        media[0].caption = text_msg
        media[0].parse_mode = ParseMode.HTML
        await context.bot.send_media_group(chat_id=chat_id, media=media)
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Выберите действие на клавиатуре:", 
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
# ОБРАБОТЧИК ДЛЯ СБОРКИ АЛЬБОМОВ
# =========================
async def handle_album(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_step = post_data.get(user_id, {}).get("step")

    # Собираем фотки только если бот их ждёт
    if current_step not in ["step_photo", "edit_photo"]:
        return

    # Проверяем, если это альбом (несколько фото)
    if update.message.media_group_id:
        album_id = update.message.media_group_id
        if album_id in processed_albums:
            return  # Игнорируем дублирующие апдейты от одной пачки фото
        processed_albums.add(album_id)
        
        await asyncio.sleep(1.0) # Даем время всем картинкам долететь
        
        # Забираем все фото из этого альбома, которые успели прийти в кэш телеграма
        updates = context.application.match_types
        media_messages = [update.message]
        
        # Собираем file_id самых больших версий фоток
        photos = []
        if current_step == "edit_photo":
            # При редактировании просто берём фотки из текущего сообщения
            photos.append(update.message.photo[-1].file_id)
        else:
            # Для нового поста ищем все фото группы
            photos.append(update.message.photo[-1].file_id)
            
        post_data[user_id]["photos"] = photos
    else:
        # Если прислали всего одну фотку
        post_data[user_id]["photos"] = [update.message.photo[-1].file_id]

    # Переключаем шаги в зависимости от режима
    if current_step == "edit_photo":
        post_data[user_id]["step"] = "final_menu"
        await show_preview(user_id, context, chat_id, text_prefix="Фото обновлено! Вот новый вариант:\n\n")
    else:
        post_data[user_id]["step"] = "step_title"
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Фото успешно добавлены📸 (Получено: {len(post_data[user_id]['photos'])} шт.)\n\nШаг 2: Введите главный заголовок вещи."
        )

# =========================
# ГЛАВНЫЙ ТЕКСТОВЫЙ ОБРАБОТЧИК
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip() if update.message.text else ""

    # Если прилетело обновление без текста (например, просто превью ссылки), игнорируем его
    if not text:
        return

    # Защита от дублирования команд (чтобы кнопки не залипали)
    if text.lower() == "пост":
        post_data[user_id] = {"step": "step_photo"}
        await update.message.reply_text(
            "Заполните пост пожалуйста.\n\nШаг 1: Отправьте фото товара (можно одну или сразу несколько!).",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    current_step = post_data.get(user_id, {}).get("step", "password")

    # 1. ПРОВЕРКА АВТОРИЗАЦИИ
    if current_step == "password":
        username = "@" + update.effective_user.username if update.effective_user.username else ""
        if username in TRUSTED_USERS or text == ADMIN_PASSWORD:
            authorized_users[user_id] = True
            post_data[user_id]["step"] = "menu"
            await update.message.reply_text(
                "Доступ подтверждён✅", 
                reply_markup=ReplyKeyboardMarkup([["пост"]], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("Пароль неверный!")
        return

    # Проверка подписки для авторизованных
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"Для использования бота подпишитесь на канал {CHANNEL_ID}")
            return
    except Forbidden:
        await update.message.reply_text("Добавьте бота в канал администратором.")
        return

    # 2. ПОШАГОВАЯ АНКЕТА
    if current_step == "step_photo":
        await update.message.reply_text("Пожалуйста, отправьте именно фотографии для Шага 1.")
        return
        
    elif current_step == "step_title":
        post_data[user_id]["title"] = text
        post_data[user_id]["step"] = "step_description"
        await update.message.reply_text("Шаг 3: Введите описание вещи.")
        return
        
    elif current_step == "step_description":
        post_data[user_id]["description"] = text
        post_data[user_id]["step"] = "step_price"
        await update.message.reply_text("Шаг 4: Введите цену.")
        return
        
    elif current_step == "step_price":
        if "BYN" not in text.upper():
            text = text + " BYN"
        post_data[user_id]["price"] = text
        post_data[user_id]["step"] = "step_size"
        await update.message.reply_text("Шаг 5: Выберите размер вещи.", reply_markup=ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True))
        return
        
    elif current_step == "step_size":
        size_input = text.upper()
        post_data[user_id]["size"] = f"{size_input} ({sizes[size_input]})" if size_input in sizes else size_input
        post_data[user_id]["step"] = "step_legit"
        await update.message.reply_text("Шаг 6: Легит? (Выберите на кнопках ниже)", reply_markup=ReplyKeyboardMarkup(legit_keyboard, resize_keyboard=True))
        return
        
    elif current_step == "step_legit":
        post_data[user_id]["legit"] = text
        post_data[user_id]["step"] = "step_kufar"
        await update.message.reply_text("Шаг 7: Впишите ссылку на Куфар.", reply_markup=ReplyKeyboardRemove())
        return
        
    elif current_step == "step_kufar":
        post_data[user_id]["kufar_link"] = text
        post_data[user_id]["step"] = "final_menu"
        await show_preview(user_id, context, chat_id, text_prefix="Вот так будет выглядеть готовый пост:\n\n")
        return

    # 3. ВЫБОР ПОЛЯ ДЛЯ РЕДАКТИРОВАНИЯ
    elif current_step == "waiting_edit_choice":
        fields_map = {
            "фото": "edit_photo", "заголовок": "title", "описание": "description",
            "цена": "price", "размер": "size", "легит": "legit", "куфар": "kufar_link"
        }
        chosen = text.lower()
        if chosen in fields_map:
            field_target = fields_map[chosen]
            if field_target == "edit_photo":
                post_data[user_id]["step"] = "edit_photo"
                await update.message.reply_text("Отправьте новое фото или пачку фотографий товара:", reply_markup=ReplyKeyboardRemove())
            else:
                post_data[user_id]["step"] = f"edit_field_{field_target}"
                if chosen == "размер":
                    await update.message.reply_text("Выберите новый размер вещи:", reply_markup=ReplyKeyboardMarkup(size_keyboard, resize_keyboard=True))
                elif chosen == "легит":
                    await update.message.reply_text("Выберите новый статус проверки:", reply_markup=ReplyKeyboardMarkup(legit_keyboard, resize_keyboard=True))
                else:
                    await update.message.reply_text(f"Введите новое значение для поля [{chosen}]:", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text("Используйте кнопки для выбора поля.", reply_markup=ReplyKeyboardMarkup(edit_menu_keyboard, resize_keyboard=True))
        return

    # 4. ДИНАМИЧЕСКОЕ ИЗМЕНЕНИЕ ТЕКСТОВОГО ПОЛЯ
    elif current_step.startswith("edit_field_"):
        field = current_step.replace("edit_field_", "")
        if field == "price" and "BYN" not in text.upper():
            text = text + " BYN"
        elif field == "size":
            text = f"{text.upper()} ({sizes[text.upper()]})" if text.upper() in sizes else text
            
        post_data[user_id][field] = text
        post_data[user_id]["step"] = "final_menu"
        await show_preview(user_id, context, chat_id, text_prefix="Пункт изменен! Новый вариант:\n\n")
        return

    # 5. ФИНАЛЬНОЕ МЕНЮ (Да / Редактировать / Отмена)
    elif current_step == "final_menu":
