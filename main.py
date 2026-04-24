import asyncio, logging, sqlite3, re, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- SOZLAMALAR ---
TOKEN = os.getenv("8787202401:AAFjQIkQrvKiZisdQwd27CuPC3Q7OwCHi3s")   # 🔐 Render/VPS environment variable
ADMIN_ID = 8588645504
ADMIN_LINK = "https://t.me/jasurbek_o10"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- DB ---
def init_db():
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS tests (kod TEXT PRIMARY KEY, javob TEXT, pdf_id TEXT)")
    cur.execute("""CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        kod TEXT,
        ball INTEGER,
        foiz REAL,
        xatolar TEXT
    )""")

    conn.commit()
    conn.close()

# --- STATES ---
class S(StatesGroup):
    kod = State()
    ans = State()

# --- HELP ---
def parse(text):
    return "".join(re.findall(r"[a-zA-Z]", text.lower()))

# --- MENU ---
def menu(uid):
    kb = [
        [KeyboardButton(text="📝 Test"), KeyboardButton(text="✅ Tekshirish")],
        [KeyboardButton(text="📊 Natijalarim"), KeyboardButton(text="📈 Dashboard")]
    ]
    if uid == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start(m: types.Message):
    init_db()

    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)",
                (m.from_user.id, m.from_user.full_name))
    conn.commit()
    conn.close()

    await m.answer("Bot ishga tushdi 🚀", reply_markup=menu(m.from_user.id))

# =========================
# 📊 DASHBOARD (STATISTIKA)
# =========================
@dp.message(F.text == "📈 Dashboard")
async def dashboard(m: types.Message):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tests")
    tests = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM results")
    results = cur.fetchone()[0]

    cur.execute("SELECT SUM(ball) FROM results")
    total_ball = cur.fetchone()[0] or 0

    conn.close()

    text = f"""
📊 <b>BOT STATISTIKA</b>

👥 Users: {users}
📝 Tests: {tests}
📄 Results: {results}
🏆 Total ball: {total_ball}

👨‍💻 Admin: {ADMIN_LINK}
"""
    await m.answer(text, parse_mode="HTML")

# =========================
# 📊 ADMIN PANEL
# =========================
@dp.message(F.text == "⚙️ Admin Panel")
async def admin(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    u = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tests")
    t = cur.fetchone()[0]

    cur.execute("SELECT SUM(ball) FROM results")
    b = cur.fetchone()[0] or 0

    conn.close()

    await m.answer(f"""
⚙️ ADMIN PANEL

👥 Users: {u}
📝 Tests: {t}
🏆 Total ball: {b}
""")

# =========================
# RUN BOT
# =========================
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("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"))
def ai_analyze(correct, user):
    prompt = f"""
Sen test tekshiruvchi AI assistentsan.

To'g'ri javoblar: {correct}
User javoblari: {user}

Quyidagilarni qil:
1. Nechta to'g'ri
2. Nechta xato
3. Qaysi savollar xato
4. Qisqa tushuntirish

Juda aniq va qisqa yoz.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content
    @dp.message(BotStates.waiting_for_answers)
async def check_answers(message: types.Message, state: FSMContext):
    data = await state.get_data()

    correct = data["correct"]
    user = parse(message.text)

    # AI analiz
    ai_result = ai_analyze(correct, user)

    # oddiy ball
    ball = sum(1 for i in range(len(correct))
               if i < len(user) and user[i] == correct[i])

    foiz = round(ball / len(correct) * 100, 1)

    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("""INSERT INTO results (user_id, kod, ball, foiz, xatolar)
                   VALUES (?,?,?,?,?)""",
                (message.from_user.id, data["kod"], ball, foiz, ai_result))
    conn.commit()
    conn.close()

    await message.answer(
        f"🏁 Natija:\n"
        f"🎯 Ball: {ball}\n"
        f"📊 Foiz: {foiz}%\n\n"
        f"🤖 AI Tahlil:\n{ai_result}"
    )

    await state.clear()
