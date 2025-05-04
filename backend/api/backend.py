from fastapi import FastAPI
from backend.llm.model import llm, get_llm_response
import uvicorn

app = FastAPI()

# Initialiser le LLM
llm()

# Route qui prend un prompt et retourne une réponseb gràce au LLM
@app.get("/llm/{prompt}")
async def get_response(prompt: str):
    try:
        answer = get_llm_response(prompt)
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)