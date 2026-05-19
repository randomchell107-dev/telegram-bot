import os
import threading
from flask import Flask
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

# =========================================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER (ЧТОБЫ БОТ НЕ ПАДАЛ С ОШИБКОЙ)
# =========================================================
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Бот запущен и работает!"

def run_flask():
    # Render сам передает порт. Если его нет, берем стандартный 10000
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()

# =========================
# НАСТРОЙКИ
# =========================

TOKEN ="8598790012:AAGQgntAxPtM-91dk3m3KbtmqTKBsUvx8gA"

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
# РАЗМЕРЫ
# =========================

sizes = {
    "XS": "140см",
    "S": "150см",
    "M": "160см",
    "L": "170см",
    "XL": "180см"
}

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    authorized_users[user_id] = False
    post_data[user_id] = {}

    await update.message.reply_text(
        "Здравствуйте предъявите пароль администратора пожалуйста.",
        reply_markup=ReplyKeyboardRemove()
    )

# =========================
# ОБРАБОТКА
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if user_id not in authorized_users:
        authorized_users[user_id] = False

    if user_id not in post_data:
        post_data[user_id] = {}

    # =========================
    # ПРОВЕРКА ПОДПИСКИ
    # =========================

    username = ""

    if update.effective_user.username:
        username = "@" + update.effective_user.username

    try:

        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )

        if member.status not in ["member", "administrator", "creator"]:

            await update.message.reply_text(
                f"Для использования бота подпишитесь на канал {CHANNEL_ID}"
            )

            return

    except Forbidden:

        await update.message.reply_text(
            "Бот не может проверить подписку.\n"
            "Добавьте бота в канал администратором."
        )

        return

    # =========================
    # ПРОВЕРКА ПАРОЛЯ
    # =========================

    if authorized_users[user_id] == False:

        # ДОВЕРЕННЫЕ ПОЛЬЗОВАТЕЛИ
        if username in TRUSTED_USERS:

            authorized_users[user_id] = True

            keyboard = [["пост"]]

            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )

            await update.message.reply_text(
                "Доступ подтверждён✅"
            )

            await update.message.reply_text(
                "Нажмите кнопку «пост» для создания поста.",
                reply_markup=reply_markup
            )

            return

        # ОБЫЧНЫЙ ПАРОЛЬ
        if update.message.text == ADMIN_PASSWORD:

            authorized_users[user_id] = True

            keyboard = [["пост"]]

            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )

            await update.message.reply_text(
                "Пароль верный, можете продолжить работу."
            )

            await update.message.reply_text(
                "Нажмите кнопку «пост» для создания поста.",
                reply_markup=reply_markup
            )

        else:

            await update.message.reply_text(
                "Пароль неверный!"
            )

        return

    # =========================
    # СОЗДАНИЕ ПОСТА
    # =========================

    if post_data[user_id] == {}:

        if update.message.text and update.message.text.lower() == "пост":

            post_data[user_id]["creating_post"] = True

            await update.message.reply_text(
                "Заполните пост пожалуйста.\n\n"
                "1. Отправьте фото.\n"
                "2. Главный заголовок.\n"
                "3. Описание.\n"
                "4. Цена.\n"
                "5. Размер.\n"
                "6. Ссылка на куфар.",
                reply_markup=ReplyKeyboardRemove()
            )

        else:

            keyboard = [["пост"]]

            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )

            await update.message.reply_text(
                "Нажмите кнопку «пост».",
                reply_markup=reply_markup
            )

        return

    # =========================
    # ФОТО
    # =========================

    if "photo" not in post_data[user_id]:

        if update.message.photo:

            photo = update.message.photo[-1].file_id

            post_data[user_id]["photo"] = photo

            await update.message.reply_text(
                "Введите главный заголовок."
            )

        else:

            await update.message.reply_text(
                "Пожалуйста отправьте фото."
            )

        return

    # =========================
    # ЗАГОЛОВОК
    # =========================

    if "title" not in post_data[user_id]:

        if update.message.text:

            post_data[user_id]["title"] = update.message.text

            await update.message.reply_text(
                "Введите описание."
            )

        return

    # =========================
    # ОПИСАНИЕ
    # =========================

    if "description" not in post_data[user_id]:

        if update.message.text:

            post_data[user_id]["description"] = update.message.text

            await update.message.reply_text(
                "Введите цену."
            )

        return

    # =========================
    # ЦЕНА
    # =========================

    if "price" not in post_data[user_id]:

        if update.message.text:

            price = update.message.text

            if "BYN" not in price.upper():
                price = price + " BYN"

            post_data[user_id]["price"] = price

            await update.message.reply_text(
                "Введите размер (XS/S/M/L/XL)."
            )

        return

    # =========================
    # РАЗМЕР
    # =========================

    if "size" not in post_data[user_id]:

        if update.message.text:

            size_input = update.message.text.upper()

            if size_input in sizes:

                full_size = f"{size_input} ({sizes[size_input]})"

            else:

                full_size = size_input

            post_data[user_id]["size"] = full_size

            await update.message.reply_text(
                "Впишите свою ссылку на куфар."
            )

        return

    # =========================
    # ССЫЛКА КУФАР
    # =========================

    if "kufar_link" not in post_data[user_id]:

        if update.message.text:

            post_data[user_id]["kufar_link"] = update.message.text

            data = post_data[user_id]

            caption = (
                f"<b><i>{data['title']}</i></b>\n\n"
                f"<blockquote>{data['description']}</blockquote>\n\n"
                f"<b>💰 Цена:</b> {data['price']}\n"
                f"<b>📏 Размер:</b> {data['size']}\n\n"
                f"✍️ <b>Писать ➡️</b> {data['kufar_link']}"
            )

            post_data[user_id]["caption"] = caption

            keyboard = [
                ["Да", "Нет"]
            ]

            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True
            )

            await update.message.reply_photo(
                photo=data["photo"],
                caption=
                f"Вот так будет выглядеть готовый пост:\n\n"
                f"{caption}\n\n"
                f"Вы подтверждаете отправку?",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )

        return

    # =========================
    # ПОДТВЕРЖДЕНИЕ
    # =========================

    text = ""

    if update.message.text:
        text = update.message.text.lower()

    if text == "да":

        data = post_data[user_id]

        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=data["photo"],
            caption=data["caption"],
            parse_mode=ParseMode.HTML
        )

        keyboard = [["пост"]]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )

        await update.message.reply_text(
            "Пост был успешно отправлен✅",
            reply_markup=reply_markup
        )

        post_data[user_id] = {}

        await update.message.reply_text(
            "Нажмите кнопку «пост» для создания нового поста."
        )

    elif text == "нет":

        keyboard = [["пост"]]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )

        post_data[user_id] = {}

        await update.message.reply_text(
            "Отправка отменена.",
            reply_markup=reply_markup
        )

    else:

        keyboard = [
            ["Да", "Нет"]
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )

        await update.message.reply_text(
            "Нажмите кнопку Да или Нет.",
            reply_markup=reply_markup
        )

# =========================
# ЗАПУСК
# =========================

def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO,
            handle_message
        )
    )

    # Запускаем фоновый веб-сервер перед стартом бота
    print("Запуск фонового веб-сервера для Render...")
    keep_alive()

    print("Бот запущен")

    app.run_polling()

if __name__ == "__main__":
    main()
