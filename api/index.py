import os
import json
import time
import telebot
from flask import Flask, request, jsonify

# O'zingizning bot tokeningizni qo'shtirnoq ichiga yozing:
TOKEN = os.environ.get("BOT_TOKEN", "9060561731:AAE66SM2-kh7qMF--X8boGEM6q_qEDDOpEw")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1758833704"))
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://displey-uzz.vercel.app")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "displey_admin_secret_token_777")

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

orders_db = []
customers_db = {}

@app.route("/", methods=["GET"])
def home():
    return "Displey-uzz Telegram WebApp & Bot ishlayapti!", 200

@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.args.get("ulash") == "1":
        host = request.headers.get("x-forwarded-host") or request.host
        proto = request.headers.get("x-forwarded-proto") or "https"
        wh_url = f"{proto}://{host}/api/index"
        success = bot.set_webhook(url=wh_url)
        return jsonify({"webhook_url": wh_url, "status": "success" if success else "failed"})

    admin_action = request.args.get("admin")
    if admin_action:
        client_token = request.headers.get("X-Admin-Token")
        if client_token != ADMIN_TOKEN:
            return jsonify({"error": "Ruxsat berilmagan"}), 401
        
        if admin_action == "data":
            return jsonify({
                "orders": orders_db,
                "customers": list(customers_db.values()),
                "persistent": False
            })
        
        elif admin_action == "update" and request.is_json:
            data = request.json
            order_id = data.get("id")
            for o in orders_db:
                if str(o.get("id")) == str(order_id):
                    if "status" in data:
                        o["status"] = data["status"]
                        if data.get("notify") and o.get("cid"):
                            try:
                                msg = f"📦 <b>Buyurtma holati o'zgardi!</b>\n\nBuyurtma: <b>#{o['id']}</b>\nYangi holat: <b>{o['status'].capitalize()}</b>"
                                bot.send_message(o["cid"], msg, parse_mode="HTML")
                            except Exception:
                                pass
                    if "note" in data:
                        o["note"] = data["note"]
                    return jsonify({"order": o})
            return jsonify({"error": "Buyurtma topilmadi"}), 404

        elif admin_action == "catalog":
            return jsonify({"products": []})

    if request.is_json:
        json_data = request.get_json(silent=True)
        if json_data:
            update = telebot.types.Update.de_json(json_data)
            bot.process_new_updates([update])
        return "OK", 200

    return "Displey-uzz API", 200

# ---------------- BOT BUYRUQLARI ----------------

@bot.message_handler(commands=["start"])
def cmd_start(message):
    cid = message.chat.id
    name = message.from_user.first_name or "Mijoz"
    username = message.from_user.username or ""
    
    customers_db[str(cid)] = {
        "cid": cid,
        "name": name,
        "username": username,
        "phone": "",
        "role": "Dona"
    }

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
        f"🚚 O'zbekiston bo'ylab BTS pochta va Taksi orqali yetkazib berish mavjud.\n\n"
        f"Displeylarni ko'rish va xarid qilish uchun pastdagi tugmani bosing 👇"
    )
    bot.send_message(cid, text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    cid = message.chat.id
    if ADMIN_ID and cid != ADMIN_ID:
        bot.send_message(cid, "⛔️ Kechirasiz, siz admin emassiz.")
        return

    admin_link = f"{WEBAPP_URL}/admin?k={ADMIN_TOKEN}"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text="⚙️ Admin panelni ochish", web_app=telebot.types.WebAppInfo(url=admin_link)))
    bot.send_message(cid, "Displey-uzz Admin paneliga kirish:", reply_markup=markup)

@bot.message_handler(content_types=["web_app_data"])
def handle_web_app(message):
    cid = message.chat.id
    try:
        raw_data = message.web_app_data.data
        data = json.loads(raw_data)

        order_id = int(time.time() * 1000) % 1000000
        order_obj = {
            "id": order_id,
            "cid": cid,
            "name": data.get("name"),
            "tg_name": message.from_user.first_name,
            "username": message.from_user.username or "",
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

        if str(cid) in customers_db:
            customers_db[str(cid)]["phone"] = data.get("phone", "")

        items_text = ""
        for it in data.get("items", []):
            items_text += f"• {it['name']} ({it['type']}) — {it['qty']} dona x {it['price']:,} so'm\n"

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
        bot.send_message(cid, user_text, parse_mode="HTML")

        if ADMIN_ID and ADMIN_ID != cid:
            admin_text = (
                f"🚨 <b>YANGI BUYURTMA #{order_id}</b>\n\n"
                f"👤 Mijoz: <b>{data.get('name')}</b> (@{message.from_user.username or 'yo\'q'})\n"
                f"📞 Tel: <code>{data.get('phone')}</code>\n"
                f"🚚 Yetkazish: <b>{data.get('delivery')}</b> - {data.get('address')}\n\n"
                f"<b>Displeylar:</b>\n{items_text}\n"
                f"💰 Jami: <b>{data.get('total_sum', 0):,} so'm</b>"
            )
            bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")

    except Exception:
        bot.send_message(cid, "Buyurtmani qabul qilishda xatolik yuz berdi.")
