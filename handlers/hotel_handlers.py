import os.path
import sys
from datetime import datetime
from aiogram import Bot, executor, types
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.storage import FSMContextProxy
from aiogram.types import ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_calendar import simple_cal_callback, SimpleCalendar, dialog_cal_callback, DialogCalendar
from keyboard.hotel_keyboards import *
from service.hotel_service import *
from functions import convert_word
from states import ClientState, HotelState
from keyboards import get_back, ikb_use_data
from config import *

from aiogram.dispatcher.filters.state import StatesGroup, State

bote = Bot(os.environ['API_TELEGRAM'])


# Запуск состояния поиска отеля
async def find_hotel_command(msg: types.Message, state: FSMContext) -> None:
    print("ss")
    await bote.send_message(chat_id=msg.chat.id, text=HOTEL_TEXT,
                            reply_markup=get_back(), parse_mode="HTML")
    await HotelState.city.set()


# Проверка города
async def check_city_command(msg: types.Message, state: FSMContext) -> None:
    print("ss")
    city = convert_word(msg.text)
    # reply_message, iata = get_city_code(city)
    city_id, name = get_city_id(city)
    print(city_id)
    if not city_id:
        await HotelState.city.set()
        await bote.send_message(chat_id=msg.chat.id, text="Не нашел такой город. Переформулируйте, пожалуйста",
                                reply_markup=get_back())
    else:
        async with state.proxy() as data:
            data["city_name"] = name
            data["city_id"] = city_id
        await HotelState.next()
        print(await state.get_state())
        await bote.send_message(chat_id=msg.chat.id, text="Дата заселения:",
                                reply_markup=await SimpleCalendar().start_calendar())


# Обработка даты прибытия
async def arrival_date_command(callback_query: CallbackQuery, callback_data: dict, state: FSMContext) -> None:
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    print(await state.get_state())
    if selected:
        if date.date() >= date.today().date():
            async with state.proxy() as data:
                data["arrival_date"] = date.strftime("%d/%m/%Y")
            await HotelState.next()
            await callback_query.message.edit_text(f'Вы выбрали дату заселения: {date.strftime("%d/%m/%Y")}')
            await callback_query.message.answer(text="Теперь укажите дату выезда:",
                                                reply_markup=await SimpleCalendar().start_calendar()
                                                )
        else:
            await callback_query.answer("В прошлое нельзя вернуться! Пожалуйста, выберите другую дату")
            await callback_query.message.delete()
            await bote.send_message(chat_id=callback_query.message.chat.id,
                                    text="Попробуйте выбрать другую дату прибытия 🤯",
                                    reply_markup=await SimpleCalendar().start_calendar())


# Обработка даты выезда
async def departure_date_command(callback_query: CallbackQuery, callback_data: dict, state: FSMContext) -> None:
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    async with state.proxy() as data:
        arrival_date = data["arrival_date"]
        arrival_date = datetime.strptime(arrival_date, "%d/%m/%Y")
    if selected:
        if date >= arrival_date:
            async with state.proxy() as data:
                data["departure_date"] = date.strftime("%d/%m/%Y")
                data["adult"] = 1
                data["kid"] = 0
                data["age1"] = 1
                data["age2"] = 1
                data["age3"] = 1
            await HotelState.next()
            await callback_query.message.edit_text(f'Вы выбрали дату выезда: {date.strftime("%d/%m/%Y")}')
            await callback_query.message.answer(text="Теперь укажите количество гостей:",
                                                reply_markup=get_guests_ikb(1, 0)
                                                )
        else:
            await callback_query.answer("В прошлое нельзя вернуться! Пожалуйста, выберите другую дату")
            await callback_query.message.delete()
            await bote.send_message(chat_id=callback_query.message.chat.id,
                                    text="Попробуйте выбрать другую дату выезда 🤯",
                                    reply_markup=await SimpleCalendar().start_calendar())


# Обработка количества гостей
async def guests_command(callback_query: CallbackQuery, state: FSMContext) -> None:
    if callback_query.data.startswith("btn_"):
        async with state.proxy() as data:
            adult = data["adult"]
            kid = data["kid"]
        print(adult)
        print(kid)
        if callback_query.data == "btn_increase_adult" and adult != 4:
            adult += 1
            await callback_query.message.edit_reply_markup(reply_markup=get_guests_ikb(adult, kid))
        elif callback_query.data == "btn_decrease_adult" and adult != 1:
            adult -= 1
            await callback_query.message.edit_reply_markup(reply_markup=get_guests_ikb(adult, kid))
        elif callback_query.data == "btn_increase_kid" and kid != 3:
            kid += 1
            await callback_query.message.edit_reply_markup(reply_markup=get_guests_ikb(adult, kid))
        elif callback_query.data == "btn_decrease_kid" and kid != 0:
            kid -= 1
            await callback_query.message.edit_reply_markup(reply_markup=get_guests_ikb(adult, kid))
        else:
            await callback_query.answer("Невозможно выполнить")

        async with state.proxy() as data:
            data["adult"] = adult
            data["kid"] = kid
    elif callback_query.data == "next":
        async with state.proxy() as data:
            kid = data["kid"]

        if kid != 0:
            # Запрос указать возраст детей
            await HotelState.next()
            TEXT_CHOOSE_AGE = "Пожалуйста, укажите возраст детей"
            await callback_query.message.edit_text(text=TEXT_CHOOSE_AGE, reply_markup=get_kid_age(kid, 1, 1, 1))
        else:
            # Поиск предложений
            await HotelState.result.set()
            async with state.proxy() as data:
                city_id = data["city_id"]
            list_filt = get_filters(city_id)
            if not list_filt:
                # результаты
                await HotelState.result.set()
                async with state.proxy() as data:
                    data["list_filters"] = list_filt
                    data["filter"] = False
            else:
                async with state.proxy() as data:
                    data["filter"] = False
                    data["list_filters"] = list_filt
                await callback_query.message.answer(text=FILTERS_TEXT, reply_markup=get_filter_ikb(list_filt, False),
                                                    parse_mode="HTML")
    else:
        pass


# Обработка возраста детей
async def kid_age_command(callback_query: CallbackQuery, state: FSMContext) -> None:
    if callback_query.data == "ignore":
        await callback_query.answer()
        return
    elif callback_query.data == "next":
        await callback_query.message.delete()
        async with state.proxy() as data:
            city_id = data["city_id"]
        list_filt = get_filters(city_id)
        if not list_filt:
            # результаты
            await HotelState.result.set()
            async with state.proxy() as data:
                data["list_filters"] = list_filt
                data["filter"] = False
        else:
            async with state.proxy() as data:
                data["filter"] = False
                data["list_filters"] = list_filt
            await callback_query.message.answer(text=FILTERS_TEXT, reply_markup=get_filter_ikb(list_filt, False),
                                                parse_mode="HTML")
            await HotelState.next()
            return

    async with state.proxy() as data:
        age1 = data["age1"]
        age2 = data["age2"]
        age3 = data["age3"]
        kid = data["kid"]

    if callback_query.data.startswith("btn_increase"):
        if callback_query.data == "btn_increase1" and age1 != 17:
            age1 += 1
            await callback_query.message.edit_reply_markup(reply_markup=get_kid_age(kid, age1, age2, age3))
        elif callback_query.data == "btn_increase2" and age2 != 17:
            age2 += 1
            await callback_query.message.edit_reply_markup(reply_markup=get_kid_age(kid, age1, age2, age3))
        elif callback_query.data == "btn_increase3" and age3 != 17:
            age3 += 1
            await callback_query.message.edit_reply_markup(reply_markup=get_kid_age(kid, age1, age2, age3))
        else:
            await callback_query.answer("Возраст детей от 0 до 17 лет")
    elif callback_query.data.startswith("btn_decrease"):
        if callback_query.data == "btn_decrease1" and age1 != 0:
            age1 -= 1
            await callback_query.message.edit_reply_markup(reply_markup=get_kid_age(kid, age1, age2, age3))
        elif callback_query.data == "btn_decrease2" and age2 != 0:
            age2 -= 1
            await callback_query.message.edit_reply_markup(reply_markup=get_kid_age(kid, age1, age2, age3))
        elif callback_query.data == "btn_decrease3" and age3 != 0:
            age3 -= 1
            await callback_query.message.edit_reply_markup(reply_markup=get_kid_age(kid, age1, age2, age3))
        else:
            await callback_query.answer("Возраст детей от 0 до 17 лет")

    async with state.proxy() as data:
        data["age1"] = age1
        data["age2"] = age2
        data["age3"] = age3


# Обработка выбора фильтров для отеля
async def filters_command(callback_query: CallbackQuery, state: FSMContext) -> None:
    if callback_query.data == "next":
        await HotelState.next()
        dict_hotel = await get_result(state)
        if dict_hotel:
            async with state.proxy() as data:
                data["info"] = dict_hotel
            ikb, photo, info = await get_hotel_view(state, 0)
            # await callback_query.message.edit_text(text=info, reply_markup=ikb, photo=photo)
        else:
            await callback_query.message.edit_text(text="По запросу ничего не найдено")
    elif callback_query.data == "ignore":
        await callback_query.answer()
    else:
        async with state.proxy() as data:
            chosen_filter = data["filter"]
            list_filt = data["list_filters"]
        if chosen_filter == callback_query.data:
            await callback_query.answer()
        else:
            await callback_query.message.edit_reply_markup(reply_markup=get_filter_ikb(list_filt, callback_query.data))
            async with state.proxy() as data:
                data["filter"] = callback_query.data


async def result_command(callback_query: CallbackQuery, state: FSMContext) -> None:
    pass


def register_hotel_handlers(dp: Dispatcher, bot: Bot, state: FSMContext) -> None:
    # dp.register_message_handler(suggest_find_hotel_command, state="ClientState.suggest_find_hotel")
    dp.register_message_handler(send_hotel, Text(equals="Отель"), state="*")
    dp.register_message_handler(find_hotel_command, Text(equals="Найти отель", ignore_case=True), state="*")
    dp.register_message_handler(check_city_command, state=HotelState.city)
    dp.register_callback_query_handler(arrival_date_command, simple_cal_callback.filter(),
                                       state=HotelState.arrival_date)
    dp.register_callback_query_handler(departure_date_command, simple_cal_callback.filter(),
                                       state=HotelState.departure_date)
    dp.register_callback_query_handler(guests_command, state=HotelState.guests)
    dp.register_callback_query_handler(kid_age_command, state=HotelState.kid_age)
    dp.register_callback_query_handler(filters_command, state=HotelState.filters)
    dp.register_callback_query_handler(result_command, state=HotelState.result)
