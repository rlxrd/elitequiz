import aiomysql
import asyncio
from app.database.models import async_session, User, Quiz, QuizQuestion, QuizAnswer, UserQuiz, Admin
from sqlalchemy import select, update, delete, desc
from sqlalchemy.orm import joinedload
from config import DB_USER, DB_PASS, DB_DB, DB_HOST


def site_connection(func):
    async def wrapper(*args, **kwargs):
        async with aiomysql.connect(
                host=DB_HOST,
                port=3306,
                user=DB_USER,
                password=DB_PASS,
                db=DB_DB
        ) as connectionz:
            async with connectionz.cursor() as cursor:
                return await func(cursor, *args, **kwargs)
    return wrapper


def connection(func):
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            return await func(session, *args, **kwargs)
    return wrapper


@connection
async def get_user(session, tg_id):
    user = await session.scalar(select(User).where(User.tg_id == tg_id))

    if not user:
        session.add(User(tg_id=tg_id))
        await session.commit()
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
    return user


@site_connection
async def get_user_from_site(cursor, phone_number):
    query = "SELECT * FROM clients WHERE phone_number_self = %s;"
    await cursor.execute(query, (phone_number,))
    result = await cursor.fetchone()
    return result


@connection
async def set_user(session, tg_id, name, number):
    await session.execute(update(User).where(User.tg_id == tg_id).values(name=name, number=number))
    await session.commit()


@connection
async def get_admin(session):
    result = await session.execute(
        select(Admin).options(joinedload(Admin.user))  # Заранее подгружаем пользователя
    )
    admins = result.scalars().all()  # Получаем все записи
    admin_ids = [admin.user.tg_id for admin in admins]
    return admin_ids

@connection
async def giveadmin(session, user_id):
    session.add(Admin(user_id=user_id))
    await session.commit()


@connection
async def ungiveadmin(session, user_id):
    await session.execute(delete(Admin).where(Admin.user_id == user_id))
    await session.commit()

@connection
async def create_quiz(session, data):
    quizzz = Quiz(name=data['name'], author=data['user'], file=data['file'])
    session.add(quizzz)
    await session.commit()
    await session.refresh(quizzz)
    return quizzz


@connection
async def create_question_answer(session, data, answers):
    question = QuizQuestion(quiz_id=data['quiz_id'], question=data['question_number'] + 1)
    session.add(question)
    await session.commit()
    await session.refresh(question)
    letters = ['A', 'B', 'C', 'D', 'F', 'E']
    values = dict(zip(letters, answers))
    for let, val in values.items():
        await asyncio.sleep(0.1)
        if val.startswith('*'):
            val = val[1:]
            session.add(QuizAnswer(quiz_question=question.id, answer=val, letter=let, is_right=True))
        else:
            session.add(QuizAnswer(quiz_question=question.id, answer=val, letter=let, is_right=False))
    await session.commit()


@connection
async def get_quiz(session, quiz_id):
    quiz = await session.scalar(select(Quiz).where(Quiz.id == quiz_id))
    return quiz


@connection
async def get_question(session, quiz_id, question):
    return await session.scalar(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id, QuizQuestion.question == question))


@connection
async def get_answers(session, question_id):
    return await session.scalars(select(QuizAnswer).where(QuizAnswer.quiz_question == question_id))


@connection
async def add_user_quiz(session, user, quiz, result):
    session.add(UserQuiz(user=user, quiz=quiz, result=result))
    await session.commit()


@connection
async def get_history(session, user_id):
    result = await session.execute(
        select(UserQuiz).where(UserQuiz.user == user_id).options(joinedload(UserQuiz.quiz_info))
    )
    history = result.scalars().all()
    return history


@connection
async def delete_quiz(session, quiz_id):
    await session.execute(delete(Quiz).where(Quiz.id == quiz_id))
    await session.commit()


@connection
async def quizlist(session):
    return await session.scalars(select(Quiz))
