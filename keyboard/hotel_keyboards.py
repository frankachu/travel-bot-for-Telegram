import json
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.callback_data import CallbackData
from service import hotel_service
from service.hotel_service import get_photo


def get_guests_ikb(adult, kid) -> InlineKeyboardMarkup:
    ikb_guests = InlineKeyboardMarkup().row(
        InlineKeyboardButton("Взрослые", callback_data="ignore"),
        InlineKeyboardButton("Дети до 17 лет", callback_data="ignore")
    ).row(
        InlineKeyboardButton("+", callback_data="btn_increase_adult"),
        InlineKeyboardButton("+", callback_data="btn_increase_kid")
    ).row(
        InlineKeyboardButton(f"{adult}", callback_data="ignore"),
        InlineKeyboardButton(f"{kid}", callback_data="ignore")
    ).row(
        InlineKeyboardButton("-", callback_data="btn_decrease_adult"),
        InlineKeyboardButton("-", callback_data="btn_decrease_kid")
    )

    ikb_guests.add(InlineKeyboardButton("Готово", callback_data="next"))

    return ikb_guests


def get_kid_age(amount, age1, age2=None, age3=None) -> InlineKeyboardMarkup:
    ikb_kid = InlineKeyboardMarkup()

    ib1 = InlineKeyboardButton("Первый ребёнок", callback_data="ignore")
    ib12 = InlineKeyboardButton("Второй ребёнок", callback_data="ignore")
    ib13 = InlineKeyboardButton("Третий ребёнок", callback_data="ignore")

    ib2 = InlineKeyboardButton("+", callback_data="btn_increase1")
    ib3 = InlineKeyboardButton(f"{age1}", callback_data="btn_ignore")
    ib4 = InlineKeyboardButton("-", callback_data="btn_decrease1")

    ib22 = InlineKeyboardButton("+", callback_data="btn_increase2")
    ib23 = InlineKeyboardButton(f"{age2}", callback_data="btn_ignore")
    ib24 = InlineKeyboardButton("-", callback_data="btn_decrease2")

    ib32 = InlineKeyboardButton("+", callback_data="btn_increase3")
    ib33 = InlineKeyboardButton(f"{age3}", callback_data="btn_ignore")
    ib34 = InlineKeyboardButton("-", callback_data="btn_decrease3")

    if amount == 1:
        ikb_kid.row(ib1).row(ib2).row(ib3).row(ib4)
    elif amount == 2:
        ikb_kid.row(ib1, ib12).row(ib2, ib22).row(ib3, ib23).row(ib4, ib24)
    elif amount == 3:
        ikb_kid.row(ib1, ib12, ib13).row(ib2, ib22, ib32).row(ib3, ib23, ib33).row(ib4, ib24, ib34)
    ikb_kid.add(InlineKeyboardButton("Готово", callback_data="next"))

    return ikb_kid


dict_filters = {"center": "Близко к центру", "rating": "Высокая оценка", "highprice": "Дорогие",
                "business": "Бизнес", "family": "Семейный", "panoramic_view": "Панорамный вид", "price": "Дешёвые"}

dict_stars = {"3stars": "⭐️⭐️⭐️", "4stars": "⭐️⭐️⭐️⭐️",
              "5stars": "⭐️⭐️⭐️⭐️⭐️"}

basic_buttons = {"Количество звезд:": "ignore", "Без звёзд": "0stars", "⭐️": "1stars", "⭐️⭐️": "2stars"}


def get_filter_ikb(list_filters, checked):
    ikb_filters = InlineKeyboardMarkup(row_width=2)
    for (index, elem) in enumerate(basic_buttons):
        value = basic_buttons.get(elem)
        if index <= 1:
            if value == checked:
                ikb_filters.add(InlineKeyboardButton(f"{elem} ✅", callback_data=f"{value}"))
            else:
                ikb_filters.add(InlineKeyboardButton(f"{elem}", callback_data=f"{value}"))
        else:
            if value == checked:
                ikb_filters.insert(InlineKeyboardButton(f"{elem} ✅", callback_data=f"{value}"))
            else:
                ikb_filters.insert(InlineKeyboardButton(f"{elem}", callback_data=f"{value}"))

    for (index, elem) in enumerate(list_filters):
        print(elem)
        if elem in dict_stars:
            value = dict_stars.get(elem)
            print(value)
            print(elem)
            if elem == checked:
                ikb_filters.insert(InlineKeyboardButton(f"{value} ✅", callback_data=f"{elem}"))
            else:
                ikb_filters.insert(InlineKeyboardButton(f"{value}", callback_data=f"{elem}"))

    ikb_filters.row(InlineKeyboardButton("Другие фильтры:", callback_data="ignore"))
    for (index, elem) in enumerate(list_filters):
        if elem in dict_filters:
            value = dict_filters.get(elem)
            print(value)
            print(elem)
            if index == 0:
                if elem == checked:
                    ikb_filters.add(InlineKeyboardButton(f"{value} ✅", callback_data=f"{elem}"))
                else:
                    ikb_filters.add(InlineKeyboardButton(f"{value}", callback_data=f"{elem}"))
            else:
                if elem == checked:
                    ikb_filters.insert(InlineKeyboardButton(f"{value} ✅", callback_data=f"{elem}"))
                else:
                    ikb_filters.insert(InlineKeyboardButton(f"{value}", callback_data=f"{elem}"))

    ikb_filters.row(InlineKeyboardButton("Дальше", callback_data="next"))

    return ikb_filters





def gg(filter):
    # Открытие файла
    f = open('spb.json', encoding="utf-8")
    # Возвращает json как словарь
    data = json.load(f)
    f.close()
    # print(type(data))

    f = open('big.json', encoding="utf-8")
    # Возвращает json как словарь
    true_price = json.load(f)
    f.close()

    for i in data[f"{filter}"]:
        hotel_id = i["hotel_id"]
        descripton = i["ty_summary"]
        price = i["last_price_info"]["price"]
        stars = i["stars"]
        if stars >= 2:
            for (index, elem) in enumerate(true_price):
                value = elem.get('hotelId')
                if value == hotel_id:
                    price_for_adult = elem.get('priceFrom')
                    print(price_for_adult)




async def get_hotel_view(state: FSMContext, index: int):
    async with state.proxy() as data:
        dict_hotel = data["info"]
    check_key = list(dict_hotel)
    # Если используется список, полученный при пересечении
    if "priceFrom" in check_key:
        id_hotel = dict_hotel[index]["hotelId"]
        photo = await get_photo(id_hotel)

        ikb = InlineKeyboardMarkup()
        return ikb, photo, "ka"

