import asyncio
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from states import Form

from database import init_db, update_user_profile, get_user, add_water, add_calories, add_burned_calories

from utils import (
    get_calories_goal,
    get_water_goal,
    get_weather_async,
    get_calories_async,
    water_progress_template,
    calories_progress_template,
)

router = Router()

@router.startup()
async def on_startup():
    await init_db()
    print("База данных подключена!")


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(
        "Добро пожаловать! Я ваш бот.\nГотов помочь вам следить за здоровьем.\nНажмите /set_profile для начала."
    )

@router.message(Command("set_profile"))
async def start_form(message: Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(Form.weight)

@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
    except ValueError:
        await message.reply("Введен неправильный вес. Введите число.")
        return

    await state.update_data(weight=weight)
    await message.answer("Введите ваш рост (в см):")
    await state.set_state(Form.height)

@router.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
    except ValueError:
        await message.reply("Введен неправильный рост. Попробуйте еще раз.")
        return

    await state.update_data(height=height)
    await message.answer("Введите ваш возраст:")
    await state.set_state(Form.age)

@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
    except ValueError:
        await message.reply("Введен неправильный возраст. Попробуйте еще раз.")
        return

    await state.update_data(age=age)
    await message.answer("Сколько минут активности у вас в день?")
    await state.set_state(Form.activity_minutes)

@router.message(Form.activity_minutes)
async def process_activity_minutes(message: Message, state: FSMContext):
    try:
        activity_minutes = float(message.text)
    except ValueError:
        await message.reply("Введено неправильное количество минут.")
        return

    await state.update_data(activity_minutes=activity_minutes)
    await message.answer("В каком городе вы находитесь?")
    await state.set_state(Form.city)

@router.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    data = await state.get_data()
    
    city = data["city"]
    weather = await get_weather_asynch(city)
    
    water_goal = get_water_goal(data["weight"], data["activity_minutes"], weather)
    calories_goal = get_calories_goal(
        data["weight"], data["activity_minutes"], data["height"], data["age"]
    )

    await update_user_profile(
        user_id=message.from_user.id,
        city=city,
        weight=data["weight"],
        height=data["height"],
        age=data["age"],
        activity_minutes=data["activity_minutes"],
        water_goal=water_goal,
        calories_goal=calories_goal
    )

    await message.answer(f"Профиль сохранен! Город: {city}. Цели рассчитаны.")
    await state.clear()

@router.message(Command("log_water"))
async def log_water(message: Message, command: CommandObject):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.reply("Сначала настройте профиль через /set_profile")
        return

    if command.args is None:
        await message.reply("Введите количество воды (например, /log_water 200)")
        return

    try:
        water_consumed = float(command.args)
    except ValueError:
        await message.reply("Ошибка: введите число.")
        return

    await add_water(user_id, water_consumed)
    
    current = user["logged_water"] + water_consumed
    goal = user["water_goal"]
    remaining = max(0, goal - current)

    await message.answer(
        f"Записано: {water_consumed} мл.\n"
        f"Всего: {current} / {goal} мл.\n"
        f"Осталось: {remaining} мл."
    )

@router.message(Command("log_food"))
async def log_food(message: Message, command: CommandObject):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.reply("Сначала настройте профиль через /set_profile")
        return

    if not command.args:
        await message.answer("Пример ввода: /log_food Банан 150")
        return

    parts = command.args.rsplit(" ", 1)
    if len(parts) != 2:
        await message.reply("Пожалуйста, введите название продукта и вес.")
        return

    food_name = parts[0]
    try:
        grams_consumed = float(parts[1])
    except ValueError:
        await message.reply("Вес должен быть числом.")
        return

    calories_per_100g = await get_calories_async(food_name)
    total_calories = calories_per_100g * (grams_consumed / 100)

    await add_calories(user_id, total_calories)

    await message.answer(
        f"🍎 {food_name} ({grams_consumed} г) — {total_calories:.1f} ккал.\n"
        f"(на 100г продукта: {calories_per_100g} ккал)"
    )

@router.message(Command("log_workout"))
async def log_workout(message: Message, command: CommandObject):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.reply("Сначала настройте профиль через /set_profile")
        return
        
    if not command.args:
        await message.reply("Пример: /log_workout Бег 30")
        return

    parts = command.args.rsplit(" ", 1)
    if len(parts) != 2:
        await message.reply("Введите тип тренировки и время в минутах.")
        return
        
    workout_type = parts[0]
    try:
        workout_time = float(parts[1])
    except ValueError:
        await message.reply("Время должно быть числом.")
        return

    burned = 300.0 
    
    await add_burned_calories(user_id, burned)
    
    extra_water_msg = ""
    if workout_time >= 30:
        extra_water = 200 * (workout_time // 30)
        extra_water_msg = f"\n💧 Рекомендую выпить дополнительно {extra_water:.0f} мл воды."

    await message.answer(
        f"🏃‍♂️ {workout_type} ({workout_time} мин) — сожжено ~{burned} ккал."
        f"{extra_water_msg}"
    )

@router.message(Command("check_progress"))
async def check_progress(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id) 

    if not user:
        await message.reply("Сначала настройте профиль через /set_profile")
        return
    
    await message.answer(
        water_progress_template.format(
            user["logged_water"],
            user["water_goal"],
            max(user["water_goal"] - user["logged_water"], 0),
        )
    )

    net_calories = user["logged_calories"] - user["burned_calories"]
    await message.answer(
        calories_progress_template.format(
            user["logged_calories"],
            user["calories_goal"],
            user["burned_calories"],
            net_calories,
        )
    )

def setup_handlers(dp):
    dp.include_router(router)