import os
import sys
from dotenv import load_dotenv
import gradio as gr
from utils.utils import dictionary_data, get_relevant_context, additional_context, chat
from utils.chunking import count_character_documents, count_tokens_documents, lanchain_loaders, divide_chunks, create_vectore_store, investigate_vectors, visualizate_embeddings_2D, visualizate_embeddings_3D
from utils.rag import connect_chroma, answer_question


load_dotenv(override=True)
openai_api_key = os.getenv('OPENAI_API_KEY')
db_name = "vector_db"
MODEL = "gpt-4.1-nano"

if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API Key not set")

def main(args: list[str]) -> int:
    # knowledge = dictionary_data("knowledge-base/empleados/*")
    # print(additional_context("¿Quién es Arcadio?", knowledge))
    # view = gr.ChatInterface(chat).launch(inbrowser=True)

    """ entire_knowledge_base = count_character_documents("knowledge-base/**/*.md")
    count_tokens_documents(MODEL, entire_knowledge_base)
    documents = lanchain_loaders("knowledge-base/*")
    chunks = divide_chunks(documents)
    vector_store = create_vectore_store(db_name, chunks)
    count, dimensions = investigate_vectors(vector_store)

    argc = len(args)
    
    if argc == 2:
        visualizate_embeddings_2D(vector_store)
    elif argc == 3:
        visualizate_embeddings_3D(vector_store) """
    
    retriever, llm = connect_chroma(db_name, MODEL)
    print(answer_question("¿Quién es Castro?", [], retriever, llm)) 
    
    gr.ChatInterface(fn=lambda message, history: answer_question(message, history, retriever, llm)).launch()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
