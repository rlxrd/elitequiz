from sqlalchemy import ForeignKey, String, BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

from datetime import datetime

from config import DB_URL

engine = create_async_engine(url=DB_URL,
                             echo=True)

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(128), nullable=True)
    number: Mapped[str] = mapped_column(String(15), nullable=True)

    admin: Mapped["Admin"] = relationship("Admin", back_populates="user", uselist=False, cascade="all, delete-orphan")
    quizzes: Mapped[list["Quiz"]] = relationship("Quiz", back_populates="author_info", cascade="all, delete-orphan")
    user_quizzes: Mapped[list["UserQuiz"]] = relationship("UserQuiz", back_populates="user_info", cascade="all, delete-orphan")


class Quiz(Base):
    __tablename__ = 'quizs'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    author: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    file: Mapped[str] = mapped_column(String(1024))

    author_info: Mapped["User"] = relationship("User", back_populates="quizzes")
    questions: Mapped[list["QuizQuestion"]] = relationship("QuizQuestion", back_populates="quiz_info", cascade="all, delete-orphan")
    user_quiz: Mapped[list["UserQuiz"]] = relationship("UserQuiz", back_populates="quiz_info", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = 'quiz_question'

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey('quizs.id', ondelete='CASCADE'))
    question: Mapped[str] = mapped_column(String(128))

    quiz_info: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")
    answers: Mapped[list["QuizAnswer"]] = relationship("QuizAnswer", back_populates="question_info", cascade="all, delete-orphan")


class QuizAnswer(Base):
    __tablename__ = 'quiz_answer'

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_question: Mapped[int] = mapped_column(ForeignKey('quiz_question.id', ondelete='CASCADE'))
    answer: Mapped[str] = mapped_column(String(128))
    letter: Mapped[str] = mapped_column(String(2))
    is_right: Mapped[bool]

    question_info: Mapped["QuizQuestion"] = relationship("QuizQuestion", back_populates="answers")


class UserQuiz(Base):
    __tablename__ = 'user_quiz'

    id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    quiz: Mapped[int] = mapped_column(ForeignKey('quizs.id', ondelete='CASCADE'))
    result: Mapped[str] = mapped_column(String(64))
    date = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    user_info: Mapped["User"] = relationship("User", back_populates="user_quizzes")
    quiz_info: Mapped["Quiz"] = relationship("Quiz", back_populates="user_quiz")


class Admin(Base):
    __tablename__ = 'admins'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

    user: Mapped["User"] = relationship("User", back_populates="admin")



async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
