import anthropic
from config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_ALBANIAN = (
    "Je një asistent studimi inteligjent për nxënësit shqiptarë. "
    "Gjithmonë përgjigju në gjuhën shqipe. "
    "Ji i qartë, i durueshëm dhe inkurajues."
)


async def _ask(system: str, user: str) -> str:
    resp = await _client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


async def chat_with_tutor(messages: list[dict], subject: str) -> str:
    subject_context = {
        "matematike": "Specializohesh në matematikë. Shpjego hap pas hapi.",
        "shqipe": "Specializohesh në gjuhën dhe letërsinë shqipe.",
    }.get(subject, "")
    system = f"{SYSTEM_ALBANIAN} {subject_context}"

    anthropic_messages = []
    for m in messages:
        if m["role"] in ("user", "assistant"):
            anthropic_messages.append({"role": m["role"], "content": m["content"]})

    if not anthropic_messages or anthropic_messages[-1]["role"] != "user":
        anthropic_messages.append({"role": "user", "content": "Vazhdoni bisedën."})

    resp = await _client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=anthropic_messages,
    )
    return resp.content[0].text


async def generate_flashcards(text: str, subject: str, count: int = 10) -> list[dict]:
    prompt = f"""
Krijo {count} kartela studimi (flashcard) bazuar në tekstin e mëposhtëm.
Lënda: {subject}
Teksti: {text}

Kthe JSON array me formatin:
[{{"front": "pyetja", "back": "përgjigja", "topic": "tema"}}]

Vetëm JSON, asgjë tjetër.
"""
    content = await _ask(SYSTEM_ALBANIAN, prompt)
    import json, re
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        return json.loads(match.group())
    return []


async def generate_quiz_questions(
    topic: str, subject: str, count: int = 5, difficulty: str = "mesatar"
) -> list[dict]:
    prompt = f"""
Gjenero {count} pyetje kuizi për lëndën "{subject}", tema "{topic}", vështirësi: {difficulty}.
Kthe JSON array me këtë format:
[{{"question": "Pyetja?", "options": ["Opsioni 1", "Opsioni 2", "Opsioni 3", "Opsioni 4"], "correct": "Opsioni 1", "explanation": "Shpjegimi."}}]
RËNDËSISHME: Fusha "correct" duhet të jetë teksti i plotë i opsionit të saktë, jo shkronja (A/B/C/D).
Vetëm JSON, asgjë tjetër.
"""
    content = await _ask(SYSTEM_ALBANIAN, prompt)
    import json, re
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        return json.loads(match.group())
    return []


async def explain_solution(question: str, subject: str) -> str:
    prompt = f"Shpjego zgjidhjen hap pas hapi për pyetjen e mëposhtme ({subject}):\n{question}"
    return await _ask(SYSTEM_ALBANIAN, prompt)


async def generate_study_plan(weak_topics: list[str], subject: str, days: int = 7) -> str:
    topics_str = ", ".join(weak_topics) if weak_topics else "tema të përgjithshme"
    prompt = (
        f"Krijo një plan studimi për {days} ditë për lëndën '{subject}'. "
        f"Temat e dobëta: {topics_str}. "
        "Jep një plan ditor konkret."
    )
    return await _ask(SYSTEM_ALBANIAN, prompt)
