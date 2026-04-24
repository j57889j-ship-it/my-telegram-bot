import asyncio, logging, sqlite3, re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- KONFIGURATSIYA ---
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

# --- YORDAMCHI FUNKSIYALAR ---
def clean_answers(text):
    """ '1a2b3c' yoki '1-a, 2-b' kabi matnlardan faqat harflarni ajratadi """
    return "".join(re.findall(r'[a-zA-Z]', text.lower()))

def main_menu(user_id):
    kb = [
        [KeyboardButton(text="📝 Test ishlash"), KeyboardButton(text="✅ Testni tekshirish")],
        [KeyboardButton(text="📊 Natijalarim"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="📞 Admin bilan bog'lanish")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Paneli")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- START BUYRUQI ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    init_db()
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (message.from_user.id, message.from_user.full_name))
    conn.commit()
    conn.close()
    await message.answer(f"Assalomu alaykum, {message.from_user.full_name}! 👋\nBotimizga xush kelibsiz!", reply_markup=main_menu(message.from_user.id))

# --- TEST ISHLASH (PDF YUKLASH) ---
@dp.message(F.text == "📝 Test ishlash")
async def show_tests(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod FROM tests")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return await message.answer("⚠️ Hozircha bazada testlar yo'q. Admin test qo'shishini kuting.")
    
    ikb = InlineKeyboardMarkup(inline_keyboard=[])
    for (kod,) in rows:
        ikb.inline_keyboard.append([InlineKeyboardButton(text=f"📄 Test kodi: {kod}", callback_data=f"getpdf_{kod}")])
    await message.answer("📚 Mavjud testlar ro'yxati:", reply_markup=ikb)

@dp.callback_query(F.data.startswith("getpdf_"))
async def send_test_pdf(call: types.CallbackQuery):
    kod = call.data.split("_")[1]
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pdf_id FROM tests WHERE kod=?", (kod,))
    res = cursor.fetchone()
    conn.close()
    if res:
        await call.message.answer_document(res[0], caption=f"✅ Test kodi: `{kod}`\n\nJavoblarni yuborish uchun '✅ Testni tekshirish' bo'limiga kiring.")
    await call.answer()

# --- TEST TEKSHIRISH VA TAHLIL ---
@dp.message(F.text == "✅ Testni tekshirish")
async def check_init(message: types.Message, state: FSMContext):
    await message.answer("🔢 Test kodini yuboring:")
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
        await message.answer(f"✅ Kod to'g'ri. Javoblarni `1a2b3c...` formatida yuboring:")
        await state.set_state(BotStates.waiting_for_answers)
    else:
        await message.answer("❌ Xatolik: Bunday kodli test topilmadi!")

@dp.message(BotStates.waiting_for_answers)
async def check_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct_ans = data['correct']
    user_ans = clean_answers(message.text)
    
    ball, xatolar = 0, []
    # Solishtirish
    for i in range(len(correct_ans)):
        u_val = user_ans[i] if i < len(user_ans) else "?"
        if u_val == correct_ans[i]:
            ball += 1
        else:
            xatolar.append(f"❌ {i+1}-savol: Siz '{u_val}', To'g'ri '{correct_ans[i]}'")

    foiz = round((ball / len(correct_ans)) * 100, 1)
    analysis_text = "\n".join(xatolar) if xatolar else "Barcha javoblar to'g'ri! 🌟"
    
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO results (user_id, kod, ball, foiz, xatolar) VALUES (?, ?, ?, ?, ?)", 
                   (message.from_user.id, data['kod'], ball, foiz, analysis_text))
    conn.commit()
    conn.close()

    await message.answer(f"🏁 **Natija:**\nTo'g'ri: {ball} ta\nSamaradorlik: {foiz}%\n\nBatafsil tahlilni '📊 Natijalarim'da ko'ring.")
    await state.clear()

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Paneli", F.from_user.id == ADMIN_ID)
async def admin_main(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Test qo'shish"), KeyboardButton(text="🗑 Testni o'chirish")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ], resize_keyboard=True)
    await message.answer("🛠 Admin boshqaruv paneli:", reply_markup=kb)

@dp.message(F.text == "➕ Test qo'shish", F.from_user.id == ADMIN_ID)
async def admin_add_start(message: types.Message, state: FSMContext):
    await message.answer("1. Test PDF faylini yuboring:")
    await state.set_state(BotStates.admin_pdf)

@dp.message(BotStates.admin_pdf, F.document)
async def admin_add_pdf(message: types.Message, state: FSMContext):
    await state.update_data(pdf_id=message.document.file_id)
    await message.answer("2. Test uchun kod kiriting:")
    await state.set_state(BotStates.admin_kod)

@dp.message(BotStates.admin_kod)
async def admin_add_kod(message: types.Message, state: FSMContext):
    await state.update_data(kod=message.text.strip())
    await message.answer("3. To'g'ri javoblarni yuboring (Masalan: `1a2b3c...`):")
    await state.set_state(BotStates.admin_ans)

@dp.message(BotStates.admin_ans)
async def admin_add_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    pure_ans = clean_answers(message.text)
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tests (kod, javob, pdf_id) VALUES (?, ?, ?)", (data['kod'], pure_ans, data['pdf_id']))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Test muvaffaqiyatli qo'shildi!\nKod: {data['kod']}", reply_markup=main_menu(ADMIN_ID))
    await state.clear()

@dp.message(F.text == "🗑 Testni o'chirish", F.from_user.id == ADMIN_ID)
async def admin_del_list(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod FROM tests")
    rows = cursor.fetchall()
    conn.close()
    if not rows: return await message.answer("Bazada o'chirish uchun test yo'q.")
    
    ikb = InlineKeyboardMarkup(inline_keyboard=[])
    for (kod,) in rows:
        ikb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ O'chirish: {kod}", callback_data=f"del_{kod}")])
    await message.answer("O'chirmoqchi bo'lgan testingizni tanlang:", reply_markup=ikb)

@dp.callback_query(F.data.startswith("del_"), F.from_user.id == ADMIN_ID)
async def admin_del_confirm(call: types.CallbackQuery):
    kod = call.data.split("_")[1]
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tests WHERE kod=?", (kod,))
    conn.commit()
    conn.close()
    await call.message.edit_text(f"🗑 Test {kod} bazadan o'chirildi.")
    await call.answer()

# --- REYTING (TO'LIQ RO'YXAT) ---
@dp.message(F.text == "🏆 Reyting")
async def rank_full(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("""SELECT users.name, SUM(results.ball) as s FROM results 
                      JOIN users ON results.user_id = users.id 
                      GROUP BY user_id ORDER BY s DESC""")
    rows = cursor.fetchall()
    conn.close()
    text = "🏆 **Global Reyting (Barcha foydalanuvchilar):**\n\n"
    for i, (name, s_ball) in enumerate(rows, 1):
        text += f"{i}. {name} — {s_ball} ball\n"
    await message.answer(text if rows else "Reyting hali shakllanmagan.")

# --- PROFIL VA NATIJALAR ---
@dp.message(F.text == "📊 Natijalarim")
async def user_results(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, kod, foiz FROM results WHERE user_id=? ORDER BY id DESC", (message.from_user.id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows: return await message.answer("Sizda hali natijalar yo'q.")
    
    ikb = InlineKeyboardMarkup(inline_keyboard=[])
    for r_id, kod, foiz in rows:
        ikb.inline_keyboard.append([InlineKeyboardButton(text=f"📊 Kod: {kod} ({foiz}%)", callback_data=f"res_{r_id}")])
    await message.answer("Topshirgan testlaringiz (Tahlilni ko'rish uchun bosing):", reply_markup=ikb)

@dp.callback_query(F.data.startswith("res_"))
async def view_detail(call: types.CallbackQuery):
    r_id = call.data.split("_")[1]
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod, ball, foiz, xatolar FROM results WHERE id=?", (r_id,))
    res = cursor.fetchone()
    conn.close()
    if res:
        await call.message.answer(f"📝 **Test {res[0]} tahlili:**\n🎯 Ball: {res[1]}\n📈 Foiz: {res[2]}%\n\n**Xatolar tahlili:**\n{res[3]}")
    await call.answer()

@dp.message(F.text == "👤 Profilim")
async def profile(message: types.Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(ball) FROM results WHERE user_id=?", (message.from_user.id,))
    res = cursor.fetchone()
    conn.close()
    await message.answer(f"👤 **Ism:** {message.from_user.full_name}\n✅ Jami yechilgan testlar: {res[0] or 0}\n🏆 Jami to'plangan ball: {res[1] or 0}")

@dp.message(F.text == "📞 Admin bilan bog'lanish")
async def contact(message: types.Message):
    await message.answer(f"Savollar bo'yicha adminga yozing: {ADMIN_LINK}")

@dp.message(F.text == "⬅️ Orqaga")
async def back(message: types.Message):
    await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())