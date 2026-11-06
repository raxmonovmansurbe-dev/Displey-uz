import os
import json
import time
import telebot
from flask import Flask, request, jsonify

TOKEN = os.environ.get("BOT_TOKEN", "9060561731:AAE66SM2-kh7qmF--X8boGEM6q_qEDDOpEw")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1758833704"))
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://displey-uzz.vercel.app")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "displey_admin_secret_token_777")

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

orders_db = []
customers_db = {}

def process_order(data, cid=None, tg_name=None, username=None):
    order_id = int(time.time() * 1000) % 1000000
    order_obj = {
        "id": order_id,
        "cid": cid,
        "name": data.get("name"),
        "tg_name": tg_name or data.get("name"),
        "username": username or "",
        "phone": data.get("phone"),
        "deliv": data.get("delivery"),
        "addr": data.get("address"),
        "pt": "Dona",
        "items": data.get("items", []),
        "qty": data.get("total_qty", 0),
        "total": data.get("total_sum", 0),
        "status": "yangi",
        "created": int(time.time() * 1000),
        "note": ""
    }
    orders_db.insert(0, order_obj)

    items_text = ""
    for it in data.get("items", []):
        items_text += f"• {it['name']} ({it['type']}) — {it['qty']} dona x {it['price']:,} so'm\n"

    # Mijozga chek yuborish (agar Telegram ID mavjud bo'lsa)
    if cid:
        user_text = (
            f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
            f"Buyurtma ID: <b>#{order_id}</b>\n"
            f"Qabul qiluvchi: <b>{data.get('name')}</b>\n"
            f"Telefon: <b>{data.get('phone')}</b>\n"
            f"Yetkazish: <b>{data.get('delivery')} ({data.get('address')})</b>\n\n"
            f"<b>Displeylar:</b>\n{items_text}\n"
            f"Jami summa: <b>{data.get('total_sum', 0):,} so'm</b>\n\n"
            f"Tez orada siz bilan bog'lanamiz! Rahmat."
        )
        try:
            bot.send_message(cid, user_text, parse_mode="HTML")
        except Exception:
            pass

    # Adminga xabar yuborish
    if ADMIN_ID:
        admin_text = (
            f"🚨 <b>YANGI BUYURTMA #{order_id}</b>\n\n"
            f"👤 Mijoz: <b>{data.get('name')}</b> (@{username or 'yoq'})\n"
            f"📞 Tel: <code>{data.get('phone')}</code>\n"
            f"🚚 Yetkazish: <b>{data.get('delivery')}</b> - {data.get('address')}\n\n"
            f"<b>Displeylar:</b>\n{items_text}\n"
            f"💰 Jami: <b>{data.get('total_sum', 0):,} so'm</b>"
        )
        try:
            bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        except Exception:
            pass

    return order_id

@app.route("/", methods=["GET"])
def home():
    return "Displey-uzz Telegram WebApp & Bot ishlayapti!", 200

# To'g'ridan-to'g'ri API orqali buyurtma qabul qilish yo'li
@app.route("/api/order", methods=["POST"])
def api_order():
    try:
        data = request.get_json(force=True)
        cid = data.get("cid")
        tg_name = data.get("tg_name")
        username = data.get("username")
        order_id = process_order(data, cid, tg_name, username)
        return jsonify({"status": "ok", "order_id": order_id}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.args.get("ulash") == "1":
        host = request.headers.get("x-forwarded-host") or request.host
        proto = request.headers.get("x-forwarded-proto") or "https"
        wh_url = f"{proto}://{host}/api/index"
        success = bot.set_webhook(url=wh_url)
        return jsonify({"webhook_url": wh_url, "status": "success" if success else "failed"})

    if request.is_json:
        json_data = request.get_json(silent=True)
        if json_data:
            update = telebot.types.Update.de_json(json_data)
            bot.process_new_updates([update])
        return "OK", 200

    return "Displey-uzz API", 200

@bot.message_handler(commands=["start"])
def cmd_start(message):
    cid = message.chat.id
    name = message.from_user.first_name or "Mijoz"
    
    markup = telebot.types.InlineKeyboardMarkup()
    btn_shop = telebot.types.InlineKeyboardButton(
        text="🛍 Do'konga kirish (Displey-uzz)",
        web_app=telebot.types.WebAppInfo(url=WEBAPP_URL)
    )
    markup.add(btn_shop)

    text = (
        f"Assalomu alaykum, <b>{name}</b>! 👋\n\n"
        f"📱 <b>Displey-uzz</b> — telefon displeylari do'koniga xush kelibsiz!\n\n"
        f"🛡 Biz barcha displeylarga <b>2 OY KAFOLAT</b> beramiz.\n"
        f"🚚 O'zbekiston bo'ylab BTS pochta va Taksi orqali yetkazib beramiz.\n\n"
        f"Displeylarni xarid qilish uchun pastdagi tugmani bosing 👇"
    )
    bot.send_message(cid, text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(content_types=["web_app_data"])
def handle_web_app(message):
    cid = message.chat.id
    try:
        raw_data = message.web_app_data.data
        data = json.loads(raw_data)
        process_order(data, cid=cid, tg_name=message.from_user.first_name, username=message.from_user.username)
    except Exception:
        pass
