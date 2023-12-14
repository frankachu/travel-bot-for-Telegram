from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.callback_data import CallbackData

# Риплай клавиатура с начальным выбором действий
kb = ReplyKeyboardMarkup(resize_keyboard=True)

b1 = KeyboardButton("Найти билеты")
b2 = KeyboardButton("Найти отель")
kb.add(b1, b2)

# Инлайн клавиатура с начальным выбором действий
cb_action = CallbackData("ikb", "action")

ikb_choose_action = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("Найти билеты", callback_data=cb_action.new('find_tickets'))],
    [InlineKeyboardButton("Найти отель", callback_data=cb_action.new('find_hotel'))],
    [InlineKeyboardButton("Заказать транфер", callback_data=cb_action.new('find_hotel'))],
    [InlineKeyboardButton("Отслеживать направление", callback_data=cb_action.new('find_hotel'))],
    [InlineKeyboardButton("Куда съездить", callback_data=cb_action.new('find_hotel'))],
])


def get_back() -> ReplyKeyboardMarkup:
    kb_back = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Главное меню"))
    return kb_back


def get_direction() -> InlineKeyboardMarkup:
    ikb_direction = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Да, лечу туда и обратно", callback_data="two_way")],
        [InlineKeyboardButton("Нет, лечу в одну сторону", callback_data="one_way")]
    ])
    return ikb_direction


def get_date_ikb() -> InlineKeyboardMarkup:
    ikb_date = InlineKeyboardMarkup(row_width=7)
    ikb_date.add(InlineKeyboardButton("Пн"), InlineKeyboardButton("Вт"), InlineKeyboardButton("Ср"),
                 InlineKeyboardButton("Чт"), InlineKeyboardButton("Пт"), InlineKeyboardButton("Сб"),
                 InlineKeyboardButton("Вс")

                 ).insert(InlineKeyboardButton("1", callback_data='1'), InlineKeyboardButton("2", callback_data='2'),
                          InlineKeyboardButton("3", callback_data='3'), InlineKeyboardButton("4", callback_data='4'),
                          InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("6", callback_data='6'),
                          InlineKeyboardButton("7", callback_data='7'))


def get_passengers_ikb(adult, kid, baby) -> InlineKeyboardMarkup:
    ikb_passengers = InlineKeyboardMarkup() \
        .row(
        InlineKeyboardButton("Взрослые", callback_data="btn_ignore"),
        InlineKeyboardButton("Дети", callback_data="btn_ignore"),
        InlineKeyboardButton("Младенцы", callback_data="btn_ignore")
    ) \
        .row(
        InlineKeyboardButton("+", callback_data="btn_increase_adult"),
        InlineKeyboardButton("+", callback_data="btn_increase_kid"),
        InlineKeyboardButton("+", callback_data="btn_increase_baby")
    ) \
        .row(
        InlineKeyboardButton(f"{adult}", callback_data="btn_ignore"),
        InlineKeyboardButton(f"{kid}", callback_data="btn_ignore"),
        InlineKeyboardButton(f"{baby}", callback_data="btn_ignore")
    ) \
        .row(
        InlineKeyboardButton("-", callback_data="btn_decrease_adult"),
        InlineKeyboardButton("-", callback_data="btn_decrease_kid"),
        InlineKeyboardButton("-", callback_data="btn_decrease_baby")
    ) \
        .add(InlineKeyboardButton("Готово", callback_data="next"))
    return ikb_passengers


