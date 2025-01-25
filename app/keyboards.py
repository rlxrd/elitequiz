from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

get_number = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text='Отправить контакт',
                        request_contact=True)]],
    input_field_placeholder='Нажмите на кнопку ниже',
    resize_keyboard=True)

auth_name = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Все верно, продолжить', callback_data='continue_reg')],
    [InlineKeyboardButton(text='Нет, это не я, сменить имя', callback_data='change_name')],
    [InlineKeyboardButton(text='Начать с начала', callback_data='back')]
])

back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Назад', callback_data='back')]
])


menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Пройти тестирование')],
    [KeyboardButton(text='Пройденные тесты')]
], input_field_placeholder='Выберите пункт меню...', resize_keyboard=True)


stop_create = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Завершить', callback_data='stop_create')]
])

start = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Начать!', callback_data='start')],
    [InlineKeyboardButton(text='Отмена!', callback_data='back')]
])

async def options_board(options: dict):
    keyboard = InlineKeyboardBuilder()
    for key in options.keys():
        keyboard.row(InlineKeyboardButton(text=key, callback_data=f"myanswer_{key}"))
    return keyboard.as_markup()
