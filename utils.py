import aiohttp
import re
from openai import AsyncOpenAI

from config import WEATHER_TOKEN, OPENROUTER_API_KEY, WEATHER_API_URL

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1", 
)

MODEL_NAME = "openai/gpt-5-nano"

SYSTEM_PROMPT = (
    "Ты экспертный диетолог. Тебе на вход передадут название продукта. "
    "Ты должен вернуть ТОЛЬКО количество калорий на 100 грамм продукта (целое число или число с плавающей точкой). "
    "Никакого лишнего текста, только число. Если продукта не существует или это не еда, верни 0."
)

def get_water_goal(weight: float, activity: float, weather_temp: float) -> float:
    """Рассчитывает норму воды."""
    base = 30 * weight
    activity_add = 500 * (activity // 30)
    weather_add = 500 if weather_temp > 25 else 0
    return float(base + activity_add + weather_add)


def get_calories_goal(weight: float, activity: float, height: float, age: int) -> float:
    """Рассчитывает норму калорий"""
    base = 10 * weight + 6.25 * height - 5 * age
    activity_add = 200 if activity > 0 else 0 
    return float(base + activity_add)


async def get_weather_async(city: str) -> float:
    """
    Асинхронно получает температуру.
    Возвращает 20.0, если город не найден или произошла ошибка API.
    """
    url = WEATHER_API_URL.format(city=city, token=WEATHER_TOKEN)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Ошибка API погоды: {response.status}")
                    return 20.0
                
                data = await response.json()
                return float(data["main"]["temp"])
    except Exception as e:
        print(f"Ошибка соединения с погодой: {e}")
        return 20.0


async def get_calories_async(food: str) -> float:
    """
    Спрашивает у LLM калорийность.
    """
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": food}
            ],
            temperature=0.2, 
        )
        
        answer = response.choices[0].message.content
        
        match = re.search(r'\d+(\.\d+)?', answer)
        
        if match:
            return float(match.group())
        else:
            print(f"LLM вернула некорректные данные: {answer}")
            return 0.0 
            
    except Exception as e:
        print(f"Ошибка OpenRouter: {e}")
        return 0.0


water_progress_template = (
    "💧 Вода:\n"
    "- Выпито: {0:.0f} мл из {1:.0f} мл.\n"
    "- Осталось: {2:.0f} мл."
)

calories_progress_template = (
    "🔥 Калории:\n"
    "- Потреблено: {0:.0f} ккал из {1:.0f} ккал.\n"
    "- Сожжено: {2:.0f} ккал.\n"
    "- Баланс (потреблено - сожжено): {3:.0f} ккал."
)