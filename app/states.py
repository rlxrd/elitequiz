from aiogram.fsm.state import State, StatesGroup


class Reg(StatesGroup):
    number = State()
    name = State()


class CreateQuiz(StatesGroup):
    get_file = State()
    get_answers = State()
    get_correct = State()


class QuizProcess(StatesGroup):
    get_id = State()
    sure = State()
    question = State()
