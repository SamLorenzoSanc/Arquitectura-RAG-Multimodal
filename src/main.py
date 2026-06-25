import os
from dotenv import load_dotenv
import gradio as gr
from openai import OpenAI
from utils.utils import dictionary_data, get_relevant_context, additional_context, chat

load_dotenv(override=True)
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API Key not set")


def main():
    #knowledge = dictionary_data("knowledge-base/empleados/*")
    #print(additional_context("¿Quién es Arcadio?", knowledge))
    view = gr.ChatInterface(chat).launch(inbrowser=True)


if __name__ == "__main__":
    main()
