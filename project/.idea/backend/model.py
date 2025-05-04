from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.vectorstores import FAISS
from huggingface_hub import InferenceClient
import torch

EMBEDDING_MODEL_NAME = "thenlper/gte-small"
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
HF_TOKEN = "TOKEN A METTRE"

client = InferenceClient(API_URL, token=HF_TOKEN)

embedding_model = None
db = None

def llm():
    global embedding_model, db

    loader = PyPDFDirectoryLoader("Utils")
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=512 // 10,
    )
    split_docs = text_splitter.split_documents(docs)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        multi_process=False,  # pour éviter problèmes FastAPI
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    db = FAISS.from_documents(
        split_docs, embedding_model, distance_strategy=DistanceStrategy.COSINE
    )

def get_llm_response(user_query):
    if db is None or embedding_model is None:
        return "Le LLM n'est pas initialisé."
    
    prompt_template = """Tu es un assistant spécialisé. Ta tâche est de répondre uniquement à la question suivante : "{question}", de manière concise et uniquement en utilisant le contexte suivant : {context}.

                        IMPORTANT : Si la question ne peut pas être répondue à partir du contexte, réponds simplement : "Je ne peux pas répondre à cette question avec les informations disponibles."

                        Réponse :
                        """


    retrieved_docs = db.similarity_search(user_query, k=5)
    context = "\n".join(
        [f"Document {i}:\n{doc.page_content}" for i, doc in enumerate(retrieved_docs)]
    )

    final_prompt = prompt_template.format(question=user_query, context=context)
    response = client.text_generation(final_prompt, max_new_tokens=500, temperature=0.1)
    print(response)
    return response
