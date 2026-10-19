"""ИИ-ассистент: системный промпт и вызов OpenAI."""

from typing import Any
import json
import urllib.error
import urllib.request

from .config import OPENAI_API_KEY, logger
from .timeutil import now_msk


def get_system_prompt(profile: dict[str, Any] | None = None) -> str:
    profile_line = ""
    if profile and (profile.get("fitness_goal") or profile.get("fitness_level")):
        profile_line = (
            "\nПрофиль пользователя для здоровья: цель — "
            f"{profile.get('fitness_goal') or 'не указана'}, уровень — {profile.get('fitness_level') or 'не указан'}. "
            "Учитывай это, когда советуешь тренировки или питание.\n"
        )
    return (
        "Ты — Life OS, дружелюбный AI-ассистент для продуктивности и здоровья. Отвечай коротко и по делу, на языке пользователя.\n"
        f"Сегодня: {now_msk().strftime('%d.%m.%Y %H:%M')} (Москва).\n"
        f"{profile_line}\n"
        "Ты умеешь:\n"
        "- Обсуждать планы, цели, мотивацию, продуктивность, привычки\n"
        "- Давать советы по организации времени и задач\n"
        "- Помогать составлять планы на день/неделю\n"
        "- Оценивать калорийность и БЖУ еды по описанию\n"
        "- Разбираться в тренировках и давать советы по ним с учётом профиля пользователя\n"
        "- Просто общаться и поддерживать\n\n"
        "Когда пользователь ЯВНО просит добавить задачу или привычку, добавь в конец ответа спец-блоки:\n"
        '<tasks>[{"name":"...","section":"work|life","priority":"high|mid|low","deadline":"YYYY-MM-DDThh:mm"|null}]</tasks>\n'
        '<habits>[{"name":"...","icon":"emoji","frequency":"Каждый день|Пн-Пт|Пн, Ср, Пт","reminder_time":"HH:MM"|null,"weekdays":[]}]</habits>\n'
        "Когда пользователь говорит, что уже СДЕЛАЛ/ВЫПОЛНИЛ существующую привычку или задачу (а не просит создать новую), добавь блок:\n"
        '<done>[{"type":"habit|task","name":"..."}]</done>\n'
        "Когда пользователь описывает, что он СЪЕЛ или ВЫПИЛ (текстом), оцени калории и БЖУ по своим знаниям и добавь блок:\n"
        '<meal>[{"description":"...","calories":число,"protein":число,"fat":число,"carbs":число}]</meal>\n'
        "Когда пользователь описывает тренировку, которую провёл, добавь блок:\n"
        '<workout>[{"type":"...","description":"...","duration_min":число,"calories":число}]</workout>\n'
        "Оценки калорий/БЖУ/тренировок делай по своим лучшим знаниям о типичных значениях — приблизительно, но разумно, не спрашивай уточнений, если пользователь не дал точных цифр.\n"
        "В name/description пиши как можно ближе к тому, как назвал пользователь.\n"
        "Если ничего из вышеперечисленного нет — НЕ добавляй соответствующие блоки.\n"
        "Не добавляй блоки, если пользователь просто разговаривает, задаёт вопросы или обсуждает что-то, не описывая конкретное действие."
    )


def call_openai(messages: list[dict[str, str]]) -> str:
    if not OPENAI_API_KEY:
        return "API-ключ OpenAI не настроен. Добавь OPENAI_API_KEY в .env файл."
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("OpenAI HTTP %s: %s", e.code, body[:500])
        return "Ошибка при обращении к AI. Проверь API-ключ и попробуй ещё раз."
    except Exception as e:
        logger.exception("OpenAI call failed: %s", e)
        return "Не удалось связаться с AI. Попробуй позже."
