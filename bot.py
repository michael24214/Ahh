from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
from config import *
import random
from PIL import Image

bot = TeleBot(API_TOKEN)

def gen_markup(prize_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=str(prize_id)))
    return markup

@bot.callback_query_handler(func=lambda call: call.data.isdigit())
def callback_query(call):
    prize_id = int(call.data)
    user_id = call.message.chat.id
    if manager.get_winners_count(prize_id) < 3:
        if manager.add_winner(user_id, prize_id):
            img = manager.get_prize_img(prize_id)
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Поздравляем! Ты получил картинку!")
        else:
            bot.send_message(user_id, 'Ты уже получил картинку!')
    else:
        bot.send_message(user_id, "К сожалению, ты не успел получить картинку! Попробуй в следующий раз!)")

def send_message(prize_count=5):
    for _ in range(prize_count):
        prize = manager.get_random_prize()
        if prize is None:
            print("Нет доступных призов для розыгрыша.")
            return
        prize_id, img = prize[:2]
        manager.mark_prize_used(prize_id)
        hide_img(img)
        users = manager.get_users()
        random.shuffle(users)  # Перемешиваем пользователей случайным образом
        for user in users[:3]:  # Отправляем сообщения только первым 3 пользователям
            with open(f'hidden_img/{img}', 'rb') as photo:
                bot.send_photo(user, photo, reply_markup=gen_markup(prize_id))
            time.sleep(1)  # Ожидание 1 секунды перед следующей отправкой
        time.sleep(1)  # Ожидание 1 секунды перед следующим розыгрышем

def send_collage(user_id):
    # Создаем коллаж из картинок, полученных пользователем
    images = manager.get_user_images(user_id)
    images = [Image.open(f'img/{img}') for img in images]
    width = max(img.width for img in images)
    height = sum(img.height for img in images)
    collage = Image.new('RGB', (width, height))
    y_offset = 0
    for img in images:
        collage.paste(img, (0, y_offset))
        y_offset += img.height
    collage.save('collage.jpg')
    with open('collage.jpg', 'rb') as photo:
        bot.send_photo(user_id, photo, caption="Ваш коллаж из полученных картинок")

def schedule_thread():
    schedule.every().hour.do(send_message)  # Здесь ты можешь задать периодичность отправки картинок
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! Добро пожаловать! 
Тебя успешно зарегистрировали!
Каждый час тебе будут приходить новые картинки и у тебя будет шанс их получить!
Для этого нужно быстрее всех нажать на кнопку 'Получить!'

Розыгрыш начнется через 30 секунд!""")
        
        # Запуск таймера для розыгрыша
        threading.Thread(target=start_raffle, args=(user_id,)).start()

def start_raffle(user_id):
    time.sleep(3)  # Ожидание 30 секунд
    send_message()  # Запуск розыгрыша
    bot.send_message(user_id, "Розыгрыш начинается прямо сейчас!")

@bot.message_handler(commands=['rating'])
def handle_rating(message):
    res = manager.get_rating()
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res
    bot.send_message(message.chat.id, res)

@bot.message_handler(commands=['collage'])
def handle_collage(message):
    user_id = message.chat.id
    send_collage(user_id)

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()
    initialize_prizes()  # Инициализация призов

    polling_thread = threading.Thread(target=polling_thread)
    polling_schedule = threading.Thread(target=schedule_thread)

    polling_thread.start()
    polling_schedule.start()
