import glob
from pathlib import Path
from openai import OpenAI

SYSTEM_PREFIX = """
Representas a AgroTech, la empresa de tecnología aplicada a los cultivos.
Eres un experto en responder preguntas sobre AgroTech, sus empleados y sus productos.
Se te proporciona información adicional que podría ser relevante para la pregunta del usuario.
Da respuestas breves y precisas. Si no sabes la respuesta, dilo.

Información relevante:
"""
MODEL = "gpt-4.1-nano"

def dictionary_data(path: str) -> dict:
    knowledge = {}

    filenames = glob.glob(path)

    for filename in filenames:
        name = Path(filename).stem.split(' ')[-1]
        with open(filename, "r", encoding="utf-8") as f:
            knowledge[name.lower()] = f.read()
    return knowledge

def get_relevant_context(message: str, knowledge: dict):
    text = ''.join(ch for ch in message if ch.isalpha() or ch.isspace())
    words = text.lower().split()
    return [knowledge[word] for word in words if word in knowledge] 

def additional_context(message:str, knowledge: dict):
    relevant_context = get_relevant_context(message, knowledge)
    if not relevant_context:
        result = "No hay ningún contexto adicional relevante para la pregunta del usuario."
    else:
        result = "El siguiente contexto adicional podría ser relevante para responder a la pregunta del usuario:\n\n"
        result += "\n\n".join(relevant_context)
    return result

def chat(message: str, history):
    openai = OpenAI()
    knowledge = dictionary_data("knowledge-base/empleados/*")

    system_message = SYSTEM_PREFIX + additional_context(message, knowledge)

    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content
  