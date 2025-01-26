import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command, Filter, CommandObject

import re
import app.keyboards as kb
import app.database.requests as rq

from app.states import Reg, CreateQuiz, QuizProcess
from app.middleware import UserMiddleware
from app.database.models import User

router = Router()
router.message.middleware(UserMiddleware())
router.callback_query.middleware(UserMiddleware())


class Admin(Filter):
    async def __call__(self, event: Message | CallbackQuery):
        return event.from_user.id in await rq.get_admin()


admin = Router()
admin.message.filter(Admin())
admin.message.middleware(UserMiddleware())
admin.callback_query.middleware(UserMiddleware())

"""
=======================
REGISTRATION PROCESS!!!
=======================
"""


def remove_non_digits(input_string):
    return ''.join(re.findall(r'\d', input_string))


@router.callback_query(F.data == 'back')
@router.message(CommandStart())
async def cmd_start(event: Message | CallbackQuery, user: User, state: FSMContext):
    user_channel_status = await event.bot.get_chat_member(chat_id=-1001976318315, user_id=event.from_user.id)

    is_message = isinstance(event, Message)
    sender = event.message if not is_message else event

    if not is_message and user_channel_status.status == 'left':
        await event.answer('🚫 Вы не подписаны!')
        return
    if user_channel_status.status == 'left':
        await sender.answer('🚫 Перед тем как начать использовать бот, подпишитесь на канал по кнопке ниже!',
                            reply_markup=kb.follow)
        return

    if not user.name:
        await sender.answer('Добро пожаловать! Для начала работы, пришлите ваш контакт.', reply_markup=kb.get_number)
        await state.set_state(Reg.number)
    else:
        await sender.answer('🤖 Доброго времени суток!', reply_markup=kb.menu)
        await state.clear()



@router.message(Reg.number, F.contact)
async def get_contact(message: Message, state: FSMContext):
    sent_message = await message.answer(text='Загрузка...', reply_markup=ReplyKeyboardRemove())

    number = f'+{message.contact.phone_number}'
    result = await rq.get_user_from_site(number)
    if result:
        await message.answer(f'Вы {result[1]} {result[2]}', reply_markup=kb.auth_name)
        await state.update_data(name=f'{result[1]} {result[2]}')
    else:
        await message.answer('Введите ваши имя и фамилию.')

    await message.bot.delete_message(chat_id=message.from_user.id,
                                     message_id=sent_message.message_id)
    await state.update_data(number=number)
    await state.set_state(Reg.name)


@router.message(Reg.number)
async def get_contact(message: Message, state: FSMContext):
    sent_message = await message.answer(text='Загрузка...', reply_markup=ReplyKeyboardRemove())

    number = f'+{remove_non_digits(message.text)}'
    result = await rq.get_user_from_site(number)
    if result:
        await message.answer(f'Вы авторизовались как {result[1]} {result[2]}', reply_markup=kb.auth_name)
        await state.update_data(name=f'{result[1]} {result[2]}')
    else:
        await message.answer('Введите ваши имя и фамилию.')

    await message.bot.delete_message(chat_id=message.from_user.id, message_id=sent_message.message_id)
    await state.update_data(number=number)
    await state.set_state(Reg.name)


@router.callback_query(Reg.name, F.data == 'change_name')
async def change_name(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer('Введите ваши имя и фамилию')


@router.callback_query(Reg.name, F.data == 'continue_reg')
async def done_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    data = await state.get_data()
    await rq.set_user(callback.from_user.id, data['name'], data['number'])
    await callback.message.answer(f'{data["name"]}, вы успешно авторизованы!', reply_markup=kb.menu)
    await state.clear()


@router.message(Reg.name)
async def new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    await rq.set_user(message.from_user.id, message.text, data['number'])
    await message.answer(f'{message.text}, вы успешно авторизованы!', reply_markup=kb.menu)
    await state.clear()


"""
=======================
USER PROFILE!!!
=======================
"""


@router.message(F.text == '🗂 Пройденные тесты')
async def my_profile(message: Message, user: User):
    results = await rq.get_history(user.id)
    if not results:
        await message.answer(f'{user.name}, у вас нет пройденных тестов.\nВаш ID: <code>{user.id}</code>')
    else:
        result = "\n".join(
            f"{quiz.quiz_info.name} | {quiz.result} | {quiz.date.strftime('%d/%m/%y %H:%M')}"
            for quiz in results
        )
        await message.answer(f'{user.name}, ниже приведена история пройденных тестов.\nВаш ID: <code>{user.id}</code>\n\n' + result)
"""
=======================
TEST PROCESS!!!
=======================
"""
@router.message(F.text == '🧮 Пройти тестирование')
async def find_test(message: Message, state: FSMContext):
    await state.set_state(QuizProcess.get_id)
    await message.answer('🆔 Введите ID теста', reply_markup=ReplyKeyboardRemove())


@router.message(QuizProcess.get_id)
async def start_test(message: Message, state: FSMContext):
    quiz = await rq.get_quiz(message.text)
    if not message.text.isdigit() or quiz is None:
        await message.answer('🆔🚫 Некорректный ID.', reply_markup=kb.back)
        return

    sent_message = await message.answer(text='🔄 Поиск квиза...',
                                        reply_markup=ReplyKeyboardRemove())
    await state.set_state(QuizProcess.sure)
    await state.update_data(quiz=quiz, question=1, history={})
    await message.answer(f'Вы хотите начать тест {quiz.name}?', reply_markup=kb.start)
    await message.bot.delete_message(chat_id=message.from_user.id,
                                     message_id=sent_message.message_id)


@router.callback_query(QuizProcess.sure, F.data == 'start')
async def start_quiz(message: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await message.answer('Удачи!')
    await message.message.answer('⏳⌛ Тест начался! Прочитайте вопрос в PDF файле и выберите вариант ответа.')
    await message.message.answer_document(document=data['quiz'].file)

    question = await rq.get_question(data['quiz'].id, data['question'])
    answers = await rq.get_answers(question.id)
    answers_list = []
    right = 0
    for answer in answers:
        answers_list.append(answer.answer)
        if answer.is_right:
            right = answer.letter

    await state.update_data(right=right)
    letters = ['A', 'B', 'C', 'D', 'F', 'E']
    values = dict(zip(letters, answers_list))
    formatted_options = "\n".join([f"{key}) {value.strip()}" for key, value in values.items()])
    await message.message.answer(f'⁉️🔠 Вопрос №{data['question']}:\n\n{formatted_options}', reply_markup=await kb.options_board(values))


@router.callback_query(F.data.startswith('myanswer_'))
async def check_answer(callback: CallbackQuery, user: User, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    ans = 'Верно' if callback.data.split('_')[1] == data['right'] else 'Ошибка'
    history = data['history']
    history[data['question']] = ans
    number = data['question'] + 1
    await state.update_data(question=number, history=history)
    data = await state.get_data()
    question = await rq.get_question(data['quiz'].id, data['question'])
    if question is None:
        print(history)
        formatted_text = "\n".join([f"{key}) {value}" for key, value in history.items()])
        correct_count = sum(1 for value in history.values() if value == 'Верно')
        error_count = sum(1 for value in history.values() if value == 'Ошибка')
        result = f"\nВерно: {correct_count}\nОшибок: {error_count}\nРезультат: {correct_count}/{correct_count + error_count}"
        await rq.add_user_quiz(user.id, data['quiz'].id, f'{correct_count}/{correct_count + error_count}')
        await callback.message.delete()
        await callback.message.answer(f'{formatted_text}\n\n{result}', reply_markup=kb.menu)
        await state.clear()
        return
    answers = await rq.get_answers(question.id)
    answers_list = []
    right = 0
    for answer in answers:
        answers_list.append(answer.answer)
        if answer.is_right:
            right = answer.letter

    await state.update_data(right=right)
    letters = ['A', 'B', 'C', 'D', 'F', 'E']
    values = dict(zip(letters, answers_list))
    formatted_options = "\n".join([f"{key}) {value.strip()}" for key, value in values.items()])
    await callback.message.edit_text(f'⁉️🔠 Вопрос №{data['question']}:\n\n{formatted_options}', reply_markup=await kb.options_board(values))


"""
=======================
ADMIN PANEL!!!
=======================
"""

@admin.message(Command('admin'))
async def admin_commands(message: Message):
    await message.answer('/createquiz name – создать квиз\n/deletequiz id – удалить квиз\n/quizlist – список квизов\n\n/giveadmin id – выдать админку\n/ungiveadmin id – удалить админа')


@admin.message(Command('giveadmin'))
async def cmd_giveadmin(message: Message, command: CommandObject):
    if command.args is None or len(command.args) > 1:
        await message.answer("Ошибка: аргументы переданы неверно!")
        return
    try:
        user_id = command.args
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n"
            "/giveadmin <id>")
        return
    await rq.giveadmin(user_id)
    await message.answer("Админ добавлен!")


@admin.message(Command('ungiveadmin'))
async def cmd_ungiveadmin(message: Message, command: CommandObject):
    if command.args is None or len(command.args) > 1:
        await message.answer("Ошибка: аргументы переданы неверно!")
        return
    try:
        user_id = command.args
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n"
            "/ungiveadmin <id>")
        return
    await rq.ungiveadmin(user_id)
    await message.answer("Админ удален!")


"""
=======================
CREATE TEST PROCESS!!!
=======================
"""


@admin.message(Command('createquiz'))
async def cmd_createquiz(message: Message, command: CommandObject, state: FSMContext):
    if command.args is None or len(command.args) < 1:
        await message.answer("Ошибка: аргументы переданы неверно!")
        return
    try:
        quiz_name = command.args
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n"
            "/createquiz name")
        return
    await state.set_state(CreateQuiz.get_file)
    await state.update_data(name=quiz_name)
    await message.answer('Пришлите документ в любом формате (pdf, docx, pptx) с вопросами.', reply_markup=ReplyKeyboardRemove())


@admin.message(CreateQuiz.get_file, F.document)
async def createquiz_getfile(message: Message, user: User, state: FSMContext):
    await state.update_data(file=message.document.file_id,
                            user=user.id)
    data = await state.get_data()
    last_quiz = await rq.create_quiz(data)
    await message.answer('Файл принят.\n\nОтправьте ответы, от 2 до 6 шт для вопроса №1. Каждый вариант ответа разделите запятой с пробелом. Правильный вариант ответа начните со звездочки.\nБудьте осторожны, если не указать правильный вариант ответа все варианты будут засчитаны как ошибка\n\nНапример:\nпервый вариант ответа, *второй вариант, третий ответ, четвертый.')
    await state.update_data(quiz_id=last_quiz.id, question_number=0)
    await state.set_state(CreateQuiz.get_answers)


@admin.message(CreateQuiz.get_answers)
async def createquiz_getanswers(message: Message, state: FSMContext):
    answers = message.text.split(', ')
    if len(answers) <= 1:
        await message.answer('Минимум два варианта ответа!')
        return

    data = await state.get_data()
    question_number = data['question_number'] + 1
    await state.update_data(question_number=question_number)

    if question_number == 6:
        await message.answer(f'Вы достигли максимума вариантов ответа!\n\nКвиз успешно создан!\n\nID для приглашения: <code>{data["quiz_id"]}</code>', reply_markup=kb.menu)
        await state.clear()
        return

    await rq.create_question_answer(data, answers)
    await message.answer(f'Принято. Введите варианты ответа для вопроса №{question_number + 1}, или закончите по кнопке ниже.', reply_markup=kb.stop_create)


@admin.callback_query(F.data == 'stop_create')
async def stop_create_quiz(callback: CallbackQuery, state: FSMContext):
    await callback.answer('Done')
    data = await state.get_data()
    await callback.message.answer(f'Квиз успешно создан!\n\nID для приглашения: <code>{data["quiz_id"]}</code>', reply_markup=kb.menu)
    await state.clear()

"""
=======================
DELETE TEST PROCESS!!!
=======================
"""

@admin.message(Command('deletequiz'))
async def cmd_deletequiz(message: Message, command: CommandObject, state: FSMContext):
    if command.args is None or len(command.args) != 1:
        await message.answer("Ошибка: аргументы переданы неверно!")
        return
    try:
        quiz_id = command.args
    except ValueError:
        await message.answer(
            "Ошибка: неправильный формат команды. Пример:\n"
            "/deletequiz id")
        return
    await rq.delete_quiz(quiz_id)
    await message.answer('Успех')


"""
=======================
DELETE TEST PROCESS!!!
=======================
"""


@admin.message(Command('quizlist'))
async def cmd_quizlist(message: Message):
    quizes = await rq.quizlist()
    quizes_list = []
    for quiz in quizes:
        quizes_list.append(f'ID: <code>{quiz.id}</code> | {quiz.name}')
    await message.answer('Созданные квизы:\n\n' + '\n'.join(quizes_list))
