import configparser
from models import Word, Person, PersonWord
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sq
import telebot
from telebot import types
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
import random

config = configparser.ConfigParser()
config.read('settings.ini')

db = config['DB']['db']
login = config['DB']['login']
password = config['DB']['password']
name = config['DB']['name']
token = config['TELEBOT']['token']

PROMPTS_NUM = 4
START_WORDS_NUM = 8
DSN = f"{db}://{login}:{password}@localhost:5432/{name}"

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(token, state_storage=state_storage)
buttons = []

class Command:
    ADD_WORD = 'Добавить слово'
    DELETE_WORD = 'Удалить слово'
    NEXT = 'Дальше'

class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()

engine = sq.create_engine(DSN)
Session = sessionmaker(bind=engine)
session = Session()


def person_exists(cid: int) -> bool:
    """ Проверяет по базе данных, существует ли пользователь с переданным message.chat.id.

    	Входные параметры:
    	cid - целочисленный message.chat.id.

    	Возвращаемое значение:
    	True - если пользователь с таким message.chat.id, иначе False.

    """
    q = session.query(Person.chat_id).select_from(Person).filter(Person.chat_id == cid).all()
    return not len(list(q)) == 0


def add_person(cid: int):
    """ Добавляет нового пользователя в таблицу Person в базе данных.

        Входные параметры:
        cid - целочисленный message.chat.id.
    """
    person = Person(chat_id=cid)
    session.add(person)
    session.commit()
    person_words = [PersonWord(id_person=person.id, id_word=id_word) for id_word in range(1, START_WORDS_NUM + 1)]
    session.add_all(person_words)
    session.commit()


def get_words(cid: int) -> list:
    """ Находит в базе данных все слова, которые сохранены у пользователя с переданным message.chat.id.

        Входные параметры:
        cid - целочисленный message.chat.id.

        Возвращаемое значение:
        Список слов, сохраненных у пользователя с переданным message.chat.id.
    """

    q = (
         session.query(Word.english).select_from(Word).
         join(PersonWord).join(Person).
         filter(Person.chat_id == cid).all()
    )

    return [line[0] for line in q]


def get_translate(word: str) -> str:
    """ Находит в базе данных перевод на русский язык переданного слова на английском.

        Входные параметры:
        word - слово на английском языке.

        Возвращаемое значение:
        Перевод слова на русский язык, взятый из базы данных.
    """
    q = session.query(Word.russian).select_from(Word).filter(Word.english == word)
    return q[0][0]


def show_target(data) -> str:
    return f"{data['target_word']} -> {data['translate_word']}"


def show_hint(*lines) -> str:
    return '\n'.join(lines)


def add_buttons(markup):
    """ Добавляет в разметку кнопки, отвечающие за добавление и удаление слова и за переход к следующему слову.

        Входные параметры:
        markup - разметка, объект типа telebot.types.ReplyKeyboardMarkup.
    """
    global buttons
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    next_btn = types.KeyboardButton(Command.NEXT)
    buttons.extend([add_word_btn, delete_word_btn, next_btn])
    markup.add(*buttons)


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    """ Обработка команд /cards и /start.
        В случае нового пользователя выводится приветственное сообщение.
        Слово выбирается случайно из базы данных слов конкретного пользователя.

        Входные параметры:
        message - объект типа telebot.types.Message, содержащий информацию о текущем пользователе.
    """
    cid = message.chat.id
    if not person_exists(cid):
        add_person(cid)
        bot.send_message(
            cid, "Привет 👋\nДавай попрактикуемся в английском языке. "
                     "Тренировки можешь проходить в удобном для себя темпе.\n\n"
                     "У тебя есть возможность использовать тренажёр, как конструктор, "
                     "и собирать свою собственную базу для обучения. Для этого воспрользуйся инструментами:\n\n"
                     "добавить слово ➕,\nудалить слово 🔙.\n\nНу что, начнём ⬇️"
        )

    words = get_words(cid)
    random.shuffle(words)
    words = words[:PROMPTS_NUM]
    target_word = random.choice(words)

    markup = types.ReplyKeyboardMarkup(row_width=2)
    global buttons
    buttons = [types.KeyboardButton(word) for word in words]
    words.remove(target_word)
    translate = get_translate(target_word)
    add_buttons(markup)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(cid, greeting, reply_markup=markup)

    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    bot.set_state(message.from_user.id, MyStates.translate_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    print('Дальше...')
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    """ Удаление текущего слова из базы данных слов пользователя.

        Входные параметры:
        message - объект типа telebot.types.Message, содержащий информацию о текущем пользователе.
    """
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        word_q = session.query(Word.id).select_from(Word).filter(Word.english == data['target_word'])
        person_q = session.query(Person.id).select_from(Person).filter(Person.chat_id == message.chat.id)
        session.query(PersonWord).filter(PersonWord.id_word == word_q[0][0] and PersonWord.id_person == person_q[0][0]).delete()
        session.commit()
        reply = f'Удалено слово "{data['translate']}"'
        bot.send_message(message.chat.id, reply)
    create_cards(message)


def fix_word(message):
    """ Запись пары слов, переданной пользователем в предыдущем сообщении, в базу данных.

        Входные параметры:
        message - объект типа telebot.types.Message, содержащий информацию о переданной паре слов и текущем пользователе.
    """
    cid = message.chat.id
    english, russian = [word.strip() for word in message.text.split('-')]
    word = Word(english=english, russian=russian)
    session.add(word)
    session.commit()

    q = session.query(Person.id).select_from(Person).filter(Person.chat_id == cid)
    person_word = PersonWord(id_person=q[0][0], id_word=word.id)
    session.add(person_word)
    session.commit()

    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    bot.set_state(message.from_user.id, MyStates.translate_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = english
        data['translate_word'] = russian

    markup = types.ReplyKeyboardMarkup(row_width=2)
    global buttons
    buttons = []
    add_buttons(markup)
    bot.send_message(message.chat.id, show_hint(
                        f"{english} -> {russian}",
                              f"В Вашем словаре {words_num(cid)} слов"
                           ),
                     reply_markup=markup
    )


def words_num(cid: int) -> int:
    num = session.query(PersonWord.id_word).join(Person).filter(Person.chat_id == cid).count()
    return num


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    msg = bot.send_message(cid, "Введите пару 'английское слово' - 'русское слово'")
    bot.register_next_step_handler(msg, fix_word)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    """ Обработка переданного пользователем ответа о переводе слова.

        Входные параметры:
        message - объект типа telebot.types.Message, содержащий информацию о выбранном и текущем пользователе.
    """
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)

            global buttons
            buttons = []
            add_buttons(markup)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint(
                    "Допущена ошибка!",
                    f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}"
            )


        bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.infinity_polling(skip_pending=True)