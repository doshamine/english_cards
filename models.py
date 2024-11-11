# Модуль с моделями таблиц для взаимодействия с базой данных

import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Word(Base):
    __tablename__ = "word"

    id = sq.Column(sq.Integer, primary_key=True)
    russian = sq.Column(sq.String(length=50), unique=True, nullable=False)
    english = sq.Column(sq.String(length=50), unique=True, nullable=False)


class Person(Base):
    __tablename__ = "person"

    id = sq.Column(sq.Integer, primary_key=True)
    chat_id = sq.Column(sq.BigInteger, nullable=False, unique=True)


class PersonWord(Base):
    __tablename__ = "person_word"

    id = sq.Column(sq.Integer, primary_key=True)
    id_word = sq.Column(sq.Integer, sq.ForeignKey("word.id"), nullable=False)
    id_person = sq.Column(sq.Integer, sq.ForeignKey("person.id"), nullable=False)

    word = relationship(Word, backref="person_word")
    person = relationship(Person, backref="person_word")