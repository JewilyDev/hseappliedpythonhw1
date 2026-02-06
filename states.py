from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity_minutes = State()
    city = State()
