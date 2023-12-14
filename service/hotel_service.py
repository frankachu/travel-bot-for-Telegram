import json
import os
from datetime import datetime

import requests
from aiogram.dispatcher import FSMContext


def get_city_code(city_name: str):
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
        success_message = "Дата заселения:"
        return success_message, name


async def get_info_hotel(state: FSMContext):
    url = "http://engine.hotellook.com/api/v2/cache.json"
    async with state.proxy() as data:
        iata = data["iata"]
        arrival_date = data["arrival_date"]
        departure_date = data["departure_date"]
        adult = data["adult"]

    currency = "rub"
    token = os.environ['TOKEN_AVIA']
    limit = 10

def get_city_id(city_name):
    city_id = False
    name = False
    # Открытие файла
    f = open('locations.json', encoding="utf-8")
    # Возвращает json как список
    data = json.load(f)
    # Итерации над списком json'ов
    for i in data:
        if i["countryId"] == "186":
            for o in i["name"]:
                for k in o.values():
                    for l in k:
                        if l["name"] == city_name:
                            city_id = i["id"]
                            name = k[0]["name"]
                            break


    f.close()

    return city_id, name

# get_city_id("Питер")

def get_filters(city_id):
    token = os.environ['TOKEN_AVIA']
    url = f"https://yasen.hotellook.com/tp/public/available_selections.json?id={city_id}&token={token}"
    responce = requests.get(url)
    if responce.status_code == 200:
        filter_list = json.loads(responce.text)
        return filter_list
    else:
        return False


async def get_result(state: FSMContext):
    token = os.environ['TOKEN_AVIA']
    default_filter = "popularity"
    async with state.proxy() as data:
        chosen_filter = data["filter"]
        arrival_date = data["arrival_date"]
        departure_date = data["departure_date"]
        city_id = data["city_id"]
        name = data["city_name"]
        adult = data["adult"]
    arrival_date = datetime.strptime(arrival_date, "%d/%m/%Y")
    arrival_date = arrival_date.strftime("%Y-%m-%d")
    departure_date = datetime.strptime(departure_date, "%d/%m/%Y")
    departure_date = departure_date.strftime("%Y-%m-%d")
    if not chosen_filter:
        url = f"http://yasen.hotellook.com/tp/public/widget_location_dump.json?currency=rub&language=ru" \
              f"&limit=15&id={city_id}&type={default_filter}&check_in={arrival_date}&check_out={departure_date}" \
              f"&token={token}"
    else:
        url = f"http://yasen.hotellook.com/tp/public/widget_location_dump.json?currency=rub&language=ru" \
              f"&limit=15&id={city_id}&type={chosen_filter}&check_in={arrival_date}&check_out={departure_date}" \
              f"&token={token}"

    responce = requests.get(url)
    #Если отели найдены
    if responce.status_code == 200:
        dict_hotel = json.loads(responce.text)
        async with state.proxy() as data:
            data["hotels"] = dict_hotel
        hotels = await get_hotel(dict_hotel, city_id, arrival_date, departure_date, adult, chosen_filter)
        if not hotels:
            print(dict_hotel)
            return dict_hotel
        else:
            return hotels
    #Отели не найдены или сервер не отвечает
    else:
        dict_hotel = False
        print("Ошибка при получении словаря с отелями по фильтру")
    return dict_hotel


async def get_hotel(dict_hotel, location_id, check_in, check_out, adult, filter):
    url = f"http://engine.hotellook.com/api/v2/cache.json?locationId={location_id}&currency=rub&adults={adult}" \
          f"&checkIn={check_in}&checkOut={check_out}&limit=200"
    responce = requests.get(url)
    # Если отели найдены
    if responce.status_code == 200:
        prices_for_adult = json.loads(responce.text)
        hotels = []
        for i in dict_hotel[f"{filter}"]:
            hotel_id = i["hotel_id"]
            descripton = i["ty_summary"]
            #price = i["last_price_info"]["price"]
            stars = i["stars"]
            if stars >= 2:
                for (index, elem) in enumerate(prices_for_adult):
                    value = elem.get('hotelId')
                    if value == hotel_id:
                        price_for_adult = elem.get('priceFrom')
                        name = elem.get('hotelName')
                        print(price_for_adult)
                        hotels.append({'hotelId': value, 'name': name, "descripton": descripton,
                                       'priceFrom': price_for_adult})
        if len(hotels) == 0:
            print("нет совпадений")
            hotels = False
        else:
            print(hotels)
            print("Есть совпадения")
    else:
        hotels = False
        print("api не дал ответ")
    return hotels

async def get_photo(id_hotel):
    #массив фото для отелей в виде словаря
    url = f"https://yasen.hotellook.com/photos/hotel_photos?id={id_hotel}"

    responce = requests.get(url)

    if responce.status_code == 200:
        dict_photos = json.loads(responce.text)
        #получить первое фото
        id_photo = dict_photos[id_hotel][0]
        # фото по id
        photo_url = f"https://photo.hotellook.com/image_v2/limit/{id_photo}/1600/1040.auto"
        print(photo_url)
    else:
        print("Не нашел фото. Надо отправить картинку по умолчанию")

