import asyncio, logging, sqlite3, re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8787202401:AAFjQIkQrvKiZisdQwd27CuPC3Q7OwCHi3s"
ADMIN_ID = 8588645504
ADMIN_LINK = "https://t.me/jasurbek_o10"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS tests (kod TEXT PRIMARY KEY, javob TEXT, pdf_id TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kod TEXT, ball INTEGER, foiz REAL, xatolar TEXT)")
    conn.commit()
    conn.close()

class BotStates(StatesGroup):
    waiting_for_kod = State()
    waiting_for_answers = State()
    admin_pdf = State()
    admin_kod = State()
    admin_ans = State()

# --- JAVOBLARNI ANIQLIKDA TAHLIL QILISH ---
def parse_answers(text):
    """ 
    Ushbu funksiya '1a2b3c' yoki '1.a 2.b' kabi matnlardan 
    faqat harflarni (a, b, c...) ajratib beradi. 
    """
    return "".join(re.findall(r'[a-zA-Z]', text.lower()))

# --- KLAVIATURA ---
def main_menu(user_id):
    kb = [
        [KeyboardButton(text="📝 Test ishlash"), KeyboardButton(text="✅ Testni tekshirish")],
        [KeyboardButton(text="📊 Natijalarim"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="📞 Admin bilan bog'lanish")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Paneli")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- BUYRUQLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    init_db()
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (message.from_user.id, message.from_user.full_name))
    conn.commit()
    conn.close()
    await message.answer(f"Assalomu alaykum, {message.from_user.full_name}! 👋", reply_markup=main_menu(message.from_user.id))

# --- TEST ISHLASH ---
@dp.message(F.text == "📝 Test ishlash")
async def list_all_tests(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod FROM tests")
    rows = cursor.fetchall()
    conn.close()
    if not rows: return await message.answer("⚠️ Hozircha bazada testlar yo'q.")
    
    ikb = InlineKeyboardMarkup(inline_keyboard=[])
    for (kod,) in rows:
        ikb.inline_keyboard.append([InlineKeyboardButton(text=f"📄 Test kodi: {kod}", callback_data=f"pdf_{kod}")])
    await message.answer("📚 Mavjud testlar:", reply_markup=ikb)

@dp.callback_query(F.data.startswith("pdf_"))
async def send_pdf(call: types.CallbackQuery):
    kod = call.data.split("_")[1]
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pdf_id FROM tests WHERE kod=?", (kod,))
    res = cursor.fetchone()
    conn.close()
    if res:
        await call.message.answer_document(res[0], caption=f"✅ Test kodi: `{kod}`")
    await call.answer()

# --- TEST TEKSHIRISH (ANIQLIK BILAN) ---
@dp.message(F.text == "✅ Testni tekshirish")
async def check_init(message: types.Message, state: FSMContext):
    await message.answer("🔢 Test kodini kiriting:")
    await state.set_state(BotStates.waiting_for_kod)

@dp.message(BotStates.waiting_for_kod)
async def check_kod(message: types.Message, state: FSMContext):
    kod = message.text.strip()
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT javob FROM tests WHERE kod=?", (kod,))
    res = cursor.fetchone()
    conn.close()
    if res:
        await state.update_data(kod=kod, correct=res[0])
        await message.answer(f"✅ Kod qabul qilindi. Javoblarni `1a2b3c...` formatida yuboring:")
        await state.set_state(BotStates.waiting_for_answers)
    else:
        await message.answer("❌ Bunday kodli test bazada topilmadi!")

@dp.message(BotStates.waiting_for_answers)
async def process_answers(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct_string = data['correct']
    user_string = parse_answers(message.text)
    
    ball, tahlil = 0, []
    # Aniqlik bilan bitta-bitta tekshirish
    for i in range(len(correct_string)):
        u_ans = user_string[i] if i < len(user_string) else "?"
        if u_ans == correct_string[i]:
            ball += 1
        else:
            tahlil.append(f"❌ {i+1}-savol: Siz '{u_ans}', To'g'ri '{correct_string[i]}'")

    foiz = round((ball / len(correct_string)) * 100, 1)
    
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO results (user_id, kod, ball, foiz, xatolar) VALUES (?, ?, ?, ?, ?)", 
                   (message.from_user.id, data['kod'], ball, foiz, "\n".join(tahlil)))
    conn.commit()
    conn.close()

    await message.answer(f"🏁 **Natijangiz:**\nTo'g'ri: {ball}\nFoiz: {foiz}%\n\nTahlilni '📊 Natijalarim'da ko'ring.")
    await state.clear()

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Paneli", F.from_user.id == ADMIN_ID)
async def admin_menu(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Test qo'shish"), KeyboardButton(text="🗑 Testni o'chirish")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ], resize_keyboard=True)
    await message.answer("🛠 Admin boshqaruv paneli:", reply_markup=kb)

@dp.message(F.text == "➕ Test qo'shish", F.from_user.id == ADMIN_ID)
async def add_start(message: types.Message, state: FSMContext):
    await message.answer("1. Test PDF faylini yuboring:")
    await state.set_state(BotStates.admin_pdf)

@dp.message(BotStates.admin_pdf, F.document)
async def add_pdf(message: types.Message, state: FSMContext):
    await state.update_data(pdf_id=message.document.file_id)
    await message.answer("2. Test kodini kiriting (masalan: 101):")
    await state.set_state(BotStates.admin_kod)

@dp.message(BotStates.admin_kod)
async def add_kod(message: types.Message, state: FSMContext):
    await state.update_data(kod=message.text.strip())
    await message.answer("3. To'g'ri javoblarni yuboring (Masalan: `1a2b3c...`):")
    await state.set_state(BotStates.admin_ans)

@dp.message(BotStates.admin_ans)
async def add_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    clean_ans = parse_answers(message.text)
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tests (kod, javob, pdf_id) VALUES (?, ?, ?)", (data['kod'], clean_ans, data['pdf_id']))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Test {data['kod']} muvaffaqiyatli qo'shildi!", reply_markup=main_menu(ADMIN_ID))
    await state.clear()

@dp.message(F.text == "🗑 Testni o'chirish", F.from_user.id == ADMIN_ID)
async def delete_list(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod FROM tests")
    rows = cursor.fetchall()
    conn.close()
    if not rows: return await message.answer("Bazada o'chirish uchun test yo'q.")
    
    ikb = InlineKeyboardMarkup(inline_keyboard=[])
    for (kod,) in rows:
        ikb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ O'chirish: {kod}", callback_data=f"del_{kod}")])
    await message.answer("O'chirmoqchi bo'lgan testni tanlang:", reply_markup=ikb)

@dp.callback_query(F.data.startswith("del_"), F.from_user.id == ADMIN_ID)
async def delete_confirm(call: types.CallbackQuery):
    kod = call.data.split("_")[1]
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tests WHERE kod=?", (kod,))
    conn.commit()
    conn.close()
    await call.message.edit_text(f"🗑 Test {kod} o'chirildi.")
    await call.answer()

# --- REYTING (TO'LIQ) ---
@dp.message(F.text == "🏆 Reyting")
async def show_ranking(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT users.name, SUM(results.ball) as s FROM results 
                      JOIN users ON results.user_id = users.id 
                      GROUP BY user_id ORDER BY s DESC""")
    rows = cursor.fetchall()
    conn.close()
    text = "🏆 **Global Reyting:**\n\n"
    for i, (name, s_ball) in enumerate(rows, 1):
        text += f"{i}. {name} — {s_ball} ball\n"
    await message.answer(text if rows else "Reyting bo'sh.")

# --- BOSHQA FUNKSIYALAR ---
@dp.message(F.text == "📊 Natijalarim")
async def my_res(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, kod, foiz FROM results WHERE user_id=? ORDER BY id DESC", (message.from_user.id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows: return await message.answer("Sizda natijalar yo'q.")
    ikb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"📊 Test: {k} ({f}%)", callback_data=f"v_{i}")] for i, k, f in rows])
    await message.answer("Natijalaringiz:", reply_markup=ikb)

@dp.callback_query(F.data.startswith("v_"))
async def view_v(call: types.CallbackQuery):
    r_id = call.data.split("_")[1]
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod, ball, foiz, xatolar FROM results WHERE id=?", (r_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        await call.message.answer(f"📝 Test: {res[0]}\n🎯 Ball: {res[1]}\n📈 Foiz: {res[2]}%\n\n**Xatolar:**\n{res[3]}")
    await call.answer()

@dp.message(F.text == "👤 Profilim")
async def profile(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(ball) FROM results WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    conn.close()
    await message.answer(f"👤 **Ism:** {message.from_user.full_name}\n✅ Testlar: {res[0] or 0}\n🏆 Ball: {res[1] or 0}")

@dp.message(F.text == "⬅️ Orqaga")
async def back_cmd(message: types.Message):
    await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
