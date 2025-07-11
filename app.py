import os
import json
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# === API CREDENTIALS ===
api_id = 21845583
api_hash = "081a3cc51a428ad292be0be4d4f4f975"
bot_token = "7905445483:AAE1kZUCLoqMf0K98i9b4gaVDmOFFcP1ZP0"

ADMIN_ID = 7597393283
SUBSCRIPTION_FILE = "subscriptions.json"
TRIAL_LIMIT = 2

app = Client("vcf_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
user_sessions = {}
trial_uses = {}

# === Subscription System ===
def load_subscriptions():
    if os.path.exists(SUBSCRIPTION_FILE):
        with open(SUBSCRIPTION_FILE, "r") as f:
            return json.load(f)
    return {}

def save_subscriptions(data):
    with open(SUBSCRIPTION_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_subscribed(user_id):
    subs = load_subscriptions()
    entry = subs.get(str(user_id))
    if not entry:
        return False
    expiry = datetime.strptime(entry["expires"], "%Y-%m-%d %H:%M:%S")
    return datetime.now() < expiry

def add_subscription(user_id, days, plan="pro"):
    subs = load_subscriptions()
    expiry = datetime.now() + timedelta(days=days)
    subs[str(user_id)] = {
        "expires": expiry.strftime("%Y-%m-%d %H:%M:%S"),
        "plan": plan
    }
    save_subscriptions(subs)

def remove_subscription(user_id):
    subs = load_subscriptions()
    if str(user_id) in subs:
        del subs[str(user_id)]
        save_subscriptions(subs)

def get_subscription_status(user_id):
    subs = load_subscriptions()
    entry = subs.get(str(user_id))
    if not entry:
        return "❌ No active subscription"
    expiry = datetime.strptime(entry["expires"], "%Y-%m-%d %H:%M:%S")
    remaining = expiry - datetime.now()
    return f"⏳ Plan: {entry['plan']} — expires in {remaining.days} days"

def is_trial_allowed(user_id):
    return trial_uses.get(str(user_id), 0) < TRIAL_LIMIT

def register_trial_use(user_id):
    trial_uses[str(user_id)] = trial_uses.get(str(user_id), 0) + 1

def unsubscribed_message():
    return (
        "❌ You are not subscribed or your subscription has expired.\n\n"
        "🧾 Available Subscription Plans:\n"
        "📆 1 Week– ₹50\n"
        "📅 1 Month – ₹180\n"
        "📆 1 Year – ₹1500\n\n"
        "📩 Contact @captainpapaji to activate your plan."
    )

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    user_id = message.from_user.id
    if not is_subscribed(user_id) and not is_trial_allowed(user_id):
        await message.reply(unsubscribed_message())
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Convert TXT to VCF", callback_data="txt_to_vcf")],
        [InlineKeyboardButton("Rename VCF Contacts", callback_data="rename_vcf")]
    ])
    await message.reply("👋 Welcome! Choose an option:", reply_markup=keyboard)

@app.on_message(filters.command("checksub"))
async def check_subscription(client, message: Message):
    await message.reply(get_subscription_status(message.from_user.id))

@app.on_message(filters.command("plans"))
async def show_plans(client, message: Message):
    await message.reply(unsubscribed_message())

@app.on_message(filters.command("addsub") & filters.user(ADMIN_ID))
async def add_sub_cmd(client, message: Message):
    try:
        _, uid, days = message.text.split()
        add_subscription(int(uid), int(days))
        await message.reply("✅ Subscription added.")
    except Exception as e:
        await message.reply(f"❌ Usage: /addsub <user_id> <days>\nError: {e}")

@app.on_message(filters.command("removesub") & filters.user(ADMIN_ID))
async def remove_sub_cmd(client, message: Message):
    try:
        _, uid = message.text.split()
        remove_subscription(int(uid))
        await message.reply("✅ Subscription removed.")
    except Exception as e:
        await message.reply(f"❌ Usage: /removesub <user_id>\nError: {e}")

@app.on_message(filters.command("extend") & filters.user(ADMIN_ID))
async def extend_sub_cmd(client, message: Message):
    try:
        _, uid, days = message.text.split()
        add_subscription(int(uid), int(days))
        await message.reply("✅ Subscription extended.")
    except Exception as e:
        await message.reply(f"❌ Usage: /extend <user_id> <days>\nError: {e}")

@app.on_message(filters.command("listsubs") & filters.user(ADMIN_ID))
async def list_subs_cmd(client, message: Message):
    subs = load_subscriptions()
    if not subs:
        await message.reply("📭 No active subscriptions.")
        return

    sorted_subs = sorted(subs.items(), key=lambda x: datetime.strptime(x[1]['expires'], "%Y-%m-%d %H:%M:%S"))

    msg = "👥 Active Subscribers (sorted by expiry):\n\n"
    for uid, info in sorted_subs:
        try:
            user = await app.get_users(int(uid))
            name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            username = f"@{user.username}" if user.username else ""
        except:
            name = "Unknown"
            username = ""
        msg += f"👤 {name} {username} ({uid}) | {info['plan']} | Expires: {info['expires']}\n"

    msg += f"\n📊 Total Subscribers: {len(subs)}"
    await message.reply(msg)

@app.on_callback_query()
async def handle_callback(client, callback_query):
    user_id = callback_query.from_user.id

    if not is_subscribed(user_id):
        if is_trial_allowed(user_id):
            register_trial_use(user_id)
        else:
            await callback_query.answer("❌ Not subscribed", show_alert=True)
            await client.send_message(user_id, unsubscribed_message())
            return

    data = callback_query.data
    if data == "txt_to_vcf":
        await callback_query.message.reply("📤 Send the `.txt` file with numbers.")
        user_sessions[user_id] = {"mode": "txt_to_vcf"}
    elif data == "rename_vcf":
        await callback_query.message.reply("📤 Send the `.vcf` file to rename.")
        user_sessions[user_id] = {"mode": "rename_vcf"}

    await callback_query.answer()

@app.on_message(filters.document)
async def handle_file(client, message: Message):
    user_id = message.from_user.id
    session = user_sessions.get(user_id)
    if not session:
        return await message.reply("❗ Use /start and tap a button first.")

    file_path = await message.download()
    if session["mode"] == "txt_to_vcf":
        session["txt_file"] = file_path
        session["awaiting"] = "country_code"
        await message.reply("if you need + then send + :")
    elif session["mode"] == "rename_vcf":
        session["vcf_file"] = file_path
        session["awaiting"] = "rename"
        await message.reply("✍️ Send: NewNamePrefix|StartNumber\nExample: Client|1")

@app.on_message(filters.text & ~filters.command(["start", "checksub", "plans", "addsub", "removesub", "extend", "listsubs"]))
async def handle_text(client, message: Message):
    user_id = message.from_user.id
    session = user_sessions.get(user_id)
    if not session or "awaiting" not in session:
        return

    try:
        if session["awaiting"] == "country_code":
            code = message.text.strip().lstrip("+")
            session["country_code"] = "+" + code
            session["awaiting"] = "prefixes"
            await message.reply("✍️ Send: ContactNamePrefix|VCFFilePrefix|StartNumber\nExample: Friend|List|1")

        elif session["awaiting"] == "prefixes":
            contact_prefix, vcf_prefix, start = message.text.strip().split("|")
            session["contact_prefix"] = contact_prefix.strip()
            session["vcf_prefix"] = vcf_prefix.strip()
            session["start_number"] = int(start)
            session["awaiting"] = "split_choice"
            await message.reply("🔀 Do you want to split VCF? (yes/no)")

        elif session["awaiting"] == "split_choice":
            if message.text.strip().lower() == "yes":
                session["split"] = True
                session["awaiting"] = "split_count"
                await message.reply("📦 How many contacts per file?")
            else:
                session["split"] = False
                await generate_vcf(client, message)

        elif session["awaiting"] == "split_count":
            session["split_count"] = int(message.text.strip())
            await generate_vcf(client, message)

        elif session["awaiting"] == "rename":
            name_prefix, start = message.text.strip().split("|")
            start = int(start)
            lines = open(session["vcf_file"], "r").read().split("BEGIN:VCARD")
            lines = [l for l in lines if l.strip()]
            output = "Renamed.vcf"

            with open(output, "w") as out:
                for i, block in enumerate(lines, start):
                    parts = block.splitlines()
                    new_block = ["BEGIN:VCARD", "VERSION:3.0"]
                    for line in parts:
                        if line.startswith("FN:"):
                            new_block.append(f"FN:{name_prefix.strip()} {i:03}")
                        elif line.startswith("TEL"):
                            new_block.append(line)
                    new_block.append("END:VCARD")
                    out.write("\n".join(new_block) + "\n")

            await message.reply_document(output, caption="✅ Renamed VCF ready.")
            os.remove(session["vcf_file"])
            os.remove(output)
            user_sessions.pop(user_id)

    except Exception as e:
        await message.reply(f"❌ Error: {e}")
        user_sessions.pop(user_id)

async def generate_vcf(client, message):
    user_id = message.from_user.id
    session = user_sessions.get(user_id)
    try:
        with open(session["txt_file"], "r") as f:
            numbers = []
            for line in f:
                num = line.strip().replace(" ", "").replace("-", "")
                if num and not num.startswith("+"):
                    num = session["country_code"] + num
                numbers.append(num)

        contact_prefix = session["contact_prefix"]
        vcf_prefix = session["vcf_prefix"]
        start = session["start_number"]

        if session.get("split"):
            count = session["split_count"]
            for idx in range(0, len(numbers), count):
                chunk = numbers[idx:idx + count]
                part_num = idx // count + 1
                filename = f"{vcf_prefix}_part_{part_num}.vcf"
                with open(filename, "w") as out:
                    for i, num in enumerate(chunk, start + idx):
                        out.write(f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_prefix} {i:03}\nTEL;TYPE=CELL:{num}\nEND:VCARD\n")
                await message.reply_document(filename, caption=f"✅ Part {part_num} ready.")
                os.remove(filename)
        else:
            filename = f"{vcf_prefix}.vcf"
            with open(filename, "w") as out:
                for i, num in enumerate(numbers, start):
                    out.write(f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_prefix} {i:03}\nTEL;TYPE=CELL:{num}\nEND:VCARD\n")
            await message.reply_document(filename, caption="✅ Your VCF file is ready.")
            os.remove(filename)

        os.remove(session["txt_file"])
        user_sessions.pop(user_id)

    except Exception as e:
        await message.reply(f"❌ Failed: {e}")
        user_sessions.pop(user_id)

# === Start Bot ===
app.run()
