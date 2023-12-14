from aiogram.dispatcher.filters.state import StatesGroup, State


class ClientState(StatesGroup):
    menu = State()
    from_city = State()
    to_city = State()
    departure_date = State()
    direction = State()
    arrival_date = State()
    passengers = State()




class HotelState(StatesGroup):
    city = State()
    arrival_date = State()
    departure_date = State()
    guests = State()
    kid_age = State()
    filters = State()
    result = State()