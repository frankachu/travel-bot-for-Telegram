import datetime
import string

from aiogram import types
import json
import requests
from aiogram.utils.callback_data import CallbackData

from config import TOKEN_API_AVIA, MARKER
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os.path


def find_city(city_name: str, direction: str):
    print(city_name)
    responce = requests.get(f"https://www.travelpayouts.com/widgets_suggest_params?q=Из%20{city_name}%20в%20Лондон")
    dict_get = eval(responce.text)
    if not dict_get:
        failure_message = "Не нашел такой город. Переформулируйте, пожалуйста"
        return failure_message, ' '
    else:
        from_city_iata = (dict_get["origin"]["iata"])
        if direction == "from":
            success_message = "👍 Теперь укажите город прибытия"
        else:
            success_message = "Дата вылета:"
        return success_message, from_city_iata


def get_city_code(city_name: str, direction: str):
    name = ""
    # Открытие файла
    f = open('cities.json', encoding="utf-8")
    # Возвращает json как словарь
    data = json.load(f)
    # Итерации над списком json'ов
    for i in data:
        if i["name"] == city_name:
            name = i["code"]
    f.close()

    if not name:
        failure_message = "Не нашел такой город. Переформулируйте, пожалуйста"
        return failure_message, ' '
    else:
        if direction == "from":
            success_message = "Теперь укажите город прибытия"
        else:
            success_message = "Дата вылета:"
        return success_message, name


def get_cheap_ticket(i, id_user, origin, destination, departure_at, direction,
                     return_at=None) -> str and InlineKeyboardMarkup:
    next_ticket_callback = CallbackData("Next", "id_ticket")

    if os.path.exists(f"{id_user}.txt"):
        f = open(f"{id_user}.txt", encoding="utf-8")

        # Возвращает json как словарь
        data = eval(json.load(f))
        print(type(data))

        i = i + 1
        price = data["data"][i]["price"]
        print(price)
        link = "https://www.aviasales.ru" + data["data"][i]["link"]
        ikb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("Купить", url=link, callback_data="buy")],
                                                    [InlineKeyboardButton(">",
                                                                          callback_data=next_ticket_callback.new(
                                                                              f"{i}"))]
                                                    ])
        return price, ikb


    else:
        url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates?"

        departure_at = departure_at.strftime("%Y-%m-%d")
        url += f"origin={origin}&destination={destination}&departure_at={departure_at}&"

        if (direction == "two_way"):
            one_way = "true"
            return_at = return_at.strftime("%Y-%m-%d")
            url += f"return_at={return_at}&"
        else:
            one_way = "false"
        url += f"sorting=price&direct=false&cy=rub&limit=30&page=1&one_way={one_way}&token={TOKEN_API_AVIA}"

        responce = requests.get(url)
        print(responce.text)
        d = responce.text.replace("true", "True")
        print(d)
        dict_get = eval(d)
        if not dict_get["data"][0]:
            failure_message = "Не нашел билеты"
            print(failure_message)
        else:
            with open(f'{id_user}.txt', 'w', encoding="utf-8") as out_file:
                json.dump(d, out_file)

            price = dict_get["data"][0]["price"]
            link = "https://www.aviasales.ru" + dict_get["data"][0]["link"]

            print(link)
            print(price)

            text_message = f"Стоимость: {price}"

            ikb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("Купить", url=link, callback_data="buy")],
                                                        [InlineKeyboardButton(">",
                                                                              callback_data=next_ticket_callback.new(
                                                                                  "0"))]
                                                        ])
            return text_message, ikb


def get_link_ticket(from_aita, to_aita, departure_date, adult, kid, baby, direction,
                    arrival_date=None) -> str:
    departure_date = datetime.datetime.strptime(departure_date, "%d/%m/%Y")
    departure_date = departure_date.strftime("%d%m")
    print(departure_date)

    url = f"https://www.aviasales.ru/?params={from_aita}{departure_date}{to_aita}"

    if direction == "two_way":
        arrival_date = datetime.datetime.strptime(arrival_date, "%d/%m/%Y")
        arrival_date = arrival_date.strftime("%d%m")
        url += f"{arrival_date}{adult}{kid}{baby}"
        print(url)
    else:
        url += f"{adult}{kid}{baby}"
    return url


async def ikb_buy(state: FSMContext) -> InlineKeyboardMarkup:
    async with state.proxy() as data:
        from_city = data["from_city"]
        to_city = data["to_city"]
        departure_date = data["departure_date"]
        adult = data["adult"]
        kid = data["kid"]
        baby = data["baby"]
        from_aita = data["from_aita"]
        to_aita = data["to_aita"]
        direction = data['direction']
        if direction == "two_way":
            arrival_date = data["arrival_date"]
            link = get_link_ticket(from_aita, to_aita, departure_date, adult, kid, baby, direction, arrival_date)
        else:
            link = get_link_ticket(from_aita, to_aita, departure_date, adult, kid, baby, direction)

    ikb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("Купить билеты", url=link)]])
    return ikb


async def get_info_ticket(state: FSMContext) -> str:
    async with state.proxy() as data:
        from_city = data["from_city"]
        to_city = data["to_city"]
        departure_date = data["departure_date"]
        adult = data["adult"]
        kid = data["kid"]
        baby = data["baby"]
        from_aita = data["from_aita"]
        to_aita = data["to_aita"]
        direction = data['direction']

    text_part1 = (
        f"""
<b>Маршрут</b>
Откуда: {from_city}
Куда: {to_city}
Дата отправления: {departure_date}
""")

    text_part3 = (f"""
<b>Пассажиры</b>
Взрослые: {adult}
Дети: {kid}
Младенцы: {baby}
""")

    if direction == "two_way":
        arrival_date = data["arrival_date"]
        text_part2 = (f"""Дата возвращения: {arrival_date}
                    """)
        link = get_link_ticket(from_aita, to_aita, departure_date, adult, kid, baby, direction,
                               arrival_date)
        text = text_part1 + text_part2 + text_part3
    else:
        text = text_part1 + text_part3
        link = get_link_ticket(from_aita, to_aita, departure_date, adult, kid, baby, direction)

    text_part4 = f"""
<b>Купить билет: {link} </b>
    """
    # text = text + text_part4
    return text


def get_tickets():
    text = ""
    reply_markup = InlineKeyboardMarkup


def convert_word(word: str):
    first_letter = word[0].upper()
    converted_word = first_letter

    capitalize_next = False

    for i, char in enumerate(word[1:]):
        if char == "-":
            capitalize_next = True
            converted_word += char
        elif capitalize_next:
            converted_word += char.upper()
            capitalize_next = False
        else:
            converted_word += char.lower()

    return converted_word
