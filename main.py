import datetime
import os
import asyncio
from aiogram import Bot, executor, types, Dispatcher
from config import TOKEN_API, HELLO_TEXT, FLY_TEXT, PASSENGERS_TEXT
from database.user import User
from keyboards import kb, get_back, get_direction, get_passengers_ikb
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from functions import get_city_code, get_info_ticket, ikb_buy
from aiogram_calendar import simple_cal_callback, SimpleCalendar
import logging
from aiogram.types import InputFile
from handlers.hotel_handlers import register_hotel_handlers
from states import ClientState
from functions import convert_word
from database.engine import create_async_engine, get_async_session_maker, proceed_schemas
from database.base import BaseModel
from sqlalchemy.engine import URL
from database import user
import psycopg2

logging.basicConfig(level=logging.INFO)

redis = RedisStorage2(host="localhost", port=6379, db=0)

bot = Bot(os.environ['API_TELEGRAM'], parse_mode="HTML")

dp = Dispatcher(bot, storage=redis)
connection = psycopg2.connect(
    host="localhost",
    user="postgres",
    password="pam",
    database="travel_bot"
)
connection.autocommit = True


def register_handler(dp: Dispatcher, bot: Bot, state: FSMContext) -> None:
    register_hotel_handlers(dp, bot, state)


async def on_startup(_):
    print('I have get started')


# Запуск бота
@dp.message_handler(commands=['start'], state="*")
async def start_command(msg: types.Message, state: FSMContext) -> None:
    await bot.send_message(chat_id=msg.chat.id, text=HELLO_TEXT, reply_markup=kb, parse_mode="HTML")

    if state is None:
        return
    await state.finish()

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT * FROM users WHERE user_id = {msg.from_user.id};
            """)
        if cursor.fetchone() is None:
            cursor.execute(
                f"""
                INSERT INTO users (user_id, username) 
                VALUES ({msg.from_user.id},'{msg.from_user.username}');
                """)


# Назад в главное меню
@dp.message_handler(Text(equals="Главное меню", ignore_case=True), state="*")
async def start_command(msg: types.Message, state: FSMContext) -> None:
    await bot.send_message(chat_id=msg.chat.id, text="Вы завершили поиск. Выберите действие в меню.", reply_markup=kb)
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()


# Обработка города отправления
@dp.message_handler(state=ClientState.from_city)
async def get_from_city(msg: types.Message, state: FSMContext):
    city = convert_word(msg.text)
    reply_message, from_aita = get_city_code(city, "from")
    if from_aita == " ":
        await ClientState.from_city.set()
    else:
        async with state.proxy() as data:
            data["from_city"] = city
            data["from_aita"] = from_aita
        await ClientState.next()
    await bot.send_message(chat_id=msg.chat.id, text=reply_message, reply_markup=get_back())


# Обработка города прибытия
@dp.message_handler(state=ClientState.to_city)
async def get_to_city(msg: types.Message, state: FSMContext):
    city = convert_word(msg.text)
    reply_message, to_aita = get_city_code(city, "to")
    print(reply_message)
    print(to_aita)
    if to_aita == " ":
        await ClientState.to_city.set()
        await bot.send_message(chat_id=msg.chat.id, text=reply_message, reply_markup=get_back())
    else:
        print(reply_message)
        print(to_aita)
        async with state.proxy() as data:
            data["to_city"] = city
            data["to_aita"] = to_aita
        await ClientState.next()
        await bot.send_message(chat_id=msg.chat.id, text=reply_message,
                               reply_markup=await SimpleCalendar().start_calendar())


# Обработка даты отправления
@dp.callback_query_handler(simple_cal_callback.filter(), state=ClientState.departure_date)
async def process_departure_date(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        if date.date() >= datetime.date.today():
            async with state.proxy() as data:
                data["departure_date"] = date.strftime("%d/%m/%Y")
            await ClientState.next()
            await callback_query.message.edit_text(f'Вы выбрали дату вылета: {date.strftime("%d/%m/%Y")}')
            await callback_query.message.answer('Ищем билет обратно?',
                                                reply_markup=get_direction()
                                                )
        else:
            await callback_query.answer("В прошлое нельзя улететь! Пожалуйста, выберите другую дату")
            await callback_query.message.delete()
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text="Попробуйте выбрать другую дату вылета 🤯",
                                   reply_markup=await SimpleCalendar().start_calendar())


# Обработка направления
@dp.callback_query_handler(state=ClientState.direction)
async def get_direct(callback_query: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data["direction"] = callback_query.data
    if callback_query.data == "two_way":
        await ClientState.next()
        await callback_query.message.edit_text(text="Ищем билет туда и обратно", reply_markup=None)
        await bot.send_message(chat_id=callback_query.message.chat.id, text="Теперь укажите дату рейса обратно:",
                               reply_markup=await SimpleCalendar().start_calendar())
    else:
        await ClientState.passengers.set()
        await callback_query.message.edit_text(text="Ищем билет в одну сторону", reply_markup=None)
        await bot.send_message(chat_id=callback_query.message.chat.id, text=PASSENGERS_TEXT,
                               reply_markup=get_passengers_ikb(1, 0, 0))
        async with state.proxy() as data:
            data["adult"] = 1
            data["kid"] = 0
            data["baby"] = 0


# Обработка даты обратно
@dp.callback_query_handler(simple_cal_callback.filter(), state=ClientState.arrival_date)
async def process_arrival_date(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    print("я тют")
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    print(selected)
    print(date)
    async with state.proxy() as data:
        departure_date = data["departure_date"]
    departure_date = datetime.datetime.strptime(departure_date, "%d/%m/%Y")
    if selected:
        if date >= departure_date:
            await ClientState.next()
            await callback_query.message.delete()
            await callback_query.message.answer(
                f'Вы выбрали {date.strftime("%d/%m/%Y")}',
                reply_markup=get_back())
            await bot.send_message(chat_id=callback_query.message.chat.id,
                                   text=PASSENGERS_TEXT,
                                   reply_markup=get_passengers_ikb(1, 0, 0))
            async with state.proxy() as data:
                data["adult"] = 1
                data["kid"] = 0
                data["baby"] = 0
                data["arrival_date"] = date.strftime("%d/%m/%Y")

        else:
            await callback_query.message.edit_text(text="Попробуйте выбрать другую дату 🤯",
                                                   reply_markup=await SimpleCalendar().start_calendar())


# Обработка количества пассажиров
@dp.callback_query_handler(state=ClientState.passengers)
async def get_passenger_amount(callback_query: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        adult = data["adult"]
        kid = data["kid"]
        baby = data["baby"]
    if callback_query.data == "btn_ignore":
        pass
    elif callback_query.data == "next":
        async with state.proxy() as data:
            data["ticket_search"] = "True"
        await bot.send_message(callback_query.message.chat.id, text=await get_info_ticket(state), parse_mode="HTML",
                               reply_markup=await ikb_buy(state))

    elif (adult + kid + baby) < 9 and callback_query.data.startswith("btn_increase"):
        if callback_query.data == "btn_increase_adult":
            adult += 1
            async with state.proxy() as data:
                data["adult"] = adult
            await callback_query.message.edit_reply_markup(reply_markup=get_passengers_ikb(adult, kid, baby))
        elif callback_query.data == "btn_increase_kid":
            kid += 1
            async with state.proxy() as data:
                data["kid"] = kid
            await callback_query.message.edit_reply_markup(reply_markup=get_passengers_ikb(adult, kid, baby))
        elif callback_query.data == "btn_increase_baby":
            if baby < adult:
                baby += 1
                async with state.proxy() as data:
                    data["baby"] = baby
                await callback_query.message.edit_reply_markup(reply_markup=get_passengers_ikb(adult, kid, baby))
            else:
                await callback_query.answer(text="Не более одного младенца на одного взрослого")
    elif callback_query.data == "btn_decrease_adult":
        if adult == 1:
            pass
        else:
            adult -= 1
            async with state.proxy() as data:
                data["adult"] = adult
            await callback_query.message.edit_reply_markup(reply_markup=get_passengers_ikb(adult, kid, baby))
    elif callback_query.data == "btn_decrease_kid":
        if kid == 0:
            pass
        else:
            kid -= 1
            async with state.proxy() as data:
                data["kid"] = kid
            await callback_query.message.edit_reply_markup(reply_markup=get_passengers_ikb(adult, kid, baby))
    elif callback_query.data == "btn_decrease_baby":
        if baby == 0:
            pass
        else:
            baby -= 1
            async with state.proxy() as data:
                data["baby"] = baby
            await callback_query.message.edit_reply_markup(reply_markup=get_passengers_ikb(adult, kid, baby))
    else:
        pass

    await callback_query.answer()


# Запуск состояния поиска билета
@dp.message_handler(Text(equals="Найти билеты", ignore_case=True))
async def tickets_command(msg: types.Message, state: FSMContext) -> None:
    await ClientState.from_city.set()
    await bot.send_message(chat_id=msg.chat.id, text=FLY_TEXT,
                           reply_markup=get_back(), parse_mode="HTML")



@dp.message_handler(Text(equals="Заказать транфер"))
async def start_command(msg: types.Message) -> None:
    await bot.send_message(chat_id=msg.chat.id, text="", reply_markup=ReplyKeyboardRemove())


@dp.message_handler(Text(equals="Отслеживать направление"))
async def start_command(msg: types.Message) -> None:
    await bot.send_message(chat_id=msg.chat.id, text="", reply_markup=ReplyKeyboardRemove())


@dp.message_handler(Text(equals="Куда съездить"))
async def start_command(msg: types.Message) -> None:
    await bot.send_message(chat_id=msg.chat.id, text="", reply_markup=ReplyKeyboardRemove())


ikb = InlineKeyboardMarkup().add(InlineKeyboardButton("Купить", callback_data="two_way",
                                                      url="https://www.aviasales.ru/search/LED1406MOW30061?request_source=search_form"),
                                 InlineKeyboardButton(">", callback_data="one_way"))


async def start():
    connection = 0
    try:
        connection = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="pam",
            database="travel_bot"
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT version();"
            )
            print(f"Server version: {cursor.fetchone()}")

        with connection.cursor() as cursor:
            cursor.execute(
                "create table if not exists users("
                "user_id int PRIMARY KEY,"
                "username varchar(32),"
                "reg_date date,"
                "upd_date date"
                ");"
            )
            print(f"Server version: {cursor.fetchone()}")
    except Exception as _ex:
        print("[INFO] Ошибка подключения к баз данных", _ex)
    finally:
        if connection:
            connection.close()
            print("[INFO] Подключение к БД завершено")



if __name__ == "__main__":
    register_handler(dp, bot, ClientState)
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)

    try:
        connection = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="pam",
            database="travel_bot"
        )
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT version();"
            )
            print(f"Server version: {cursor.fetchone()}")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS public.users(
                    user_id int PRIMARY KEY,
                    username varchar(32) NOT NULL,
                    reg_date date  NOT NULL DEFAULT CURRENT_DATE,
                    upd_date date  NOT NULL DEFAULT CURRENT_DATE
                );
                """)
        with connection.cursor() as cursor:
            cursor.execute(
                """       
                CREATE TABLE IF NOT EXISTS public.hotel_city(
                    city_code int PRIMARY KEY,
                    name varchar(32) NOT NULL,
                    filters TEXT,
                    upd_date date  NOT NULL DEFAULT CURRENT_DATE
                );
                """)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS public.hotel_search(
                    id SERIAL PRIMARY KEY,
                    user_id int NOT NULL,
                    city_code int NOT NULL,
                    departure_date date NOT NULL,
                    return_date date,
                    adults int,
                    kid int,
                    baby int,
                    upd_date date,
                
                
                    CONSTRAINT fk_user_id FOREIGN KEY (user_id)
                        REFERENCES public.users (user_id) MATCH SIMPLE
                        ON UPDATE CASCADE
                        ON DELETE NO ACTION,
                        
                    CONSTRAINT fk_city_code FOREIGN KEY (city_code)
                        REFERENCES public.hotel_city (city_code) MATCH SIMPLE
                        ON UPDATE CASCADE
                        ON DELETE NO ACTION);
                """
            )

            with connection.cursor() as cursor:
                cursor.execute(
                    """       
                    CREATE TABLE IF NOT EXISTS public.ticket_city(
                        iata varchar(3) PRIMARY KEY,
                        name_city varchar(32) NOT NULL,
                        upd_date date  NOT NULL DEFAULT CURRENT_DATE
                    );
                    """)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.hotel_search(
                        id SERIAL PRIMARY KEY,
                        user_id int NOT NULL,
                        city_code int NOT NULL,
                        departure_date date NOT NULL,
                        return_date date,
                        adults int,
                        kid int,
                        baby int,
                        upd_date date,


                        CONSTRAINT fk_user_id FOREIGN KEY (user_id)
                            REFERENCES public.users (user_id) MATCH SIMPLE
                            ON UPDATE CASCADE
                            ON DELETE NO ACTION,

                        CONSTRAINT fk_city_code FOREIGN KEY (city_code)
                            REFERENCES public.hotel_city (city_code) MATCH SIMPLE
                            ON UPDATE CASCADE
                            ON DELETE NO ACTION);
                    """
                )
            print("[INFO] Таблицы созданы")
    except Exception as _ex:
        print("[INFO] Ошибка подключения к баз данных", _ex)
    finally:
        if connection:
            connection.close()
            print("[INFO] Подключение к БД завершено")

