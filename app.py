import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel

from retriever import retrieve_relevant_chunks


# Load environment variables from a .env file if the user creates one.
load_dotenv()


# Create the FastAPI web application.
api = FastAPI(title="SkyGrid RAG Chatbot API")


class ChatRequest(BaseModel):
    """The JSON body the /chat endpoint expects."""

    # The user's question, for example: {"message": "What is SkyGrid?"}
    message: str


class ChatResponse(BaseModel):
    """The JSON body the /chat endpoint returns."""

    # The chatbot answer, for example: {"reply": "SkyGrid is..."}
    reply: str


@api.get("/")
def root():
    """Return a friendly welcome message and list the main API endpoints."""
    # This helps users confirm the API is running when they open it in a browser.
    return {
        "message": "Welcome to SkyGrid RAG Chatbot API.",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
        },
    }


@api.get("/health")
def health_check():
    """Return a simple status so hosting platforms know the API is alive."""
    # This endpoint does not call Gemini or ChromaDB, so it should be fast and reliable.
    return {"status": "ok"}


def build_prompt(question, chunks):
    """Create the prompt that sends retrieved context to the LLM."""
    context_parts = []

    # Format each retrieved chunk with a source label.
    for index, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"Source {index}: {chunk['source']}\n{chunk['text']}"
        )

    # Join all retrieved chunks into one context block.
    context = "\n\n".join(context_parts)

    # Give the LLM clear instructions and the user's question.
    return f"""
You are SkyGrid RAG Chatbot, a helpful assistant that answers using the provided context.

Rules:
- Answer only from the context when possible.
- If the answer is not in the context, say you do not know based on the documents.
- Keep the answer clear and beginner-friendly.
- Mention the source file names you used.

Context:
{context}

Question:
{question}
"""


def ask_llm(question, chunks):
    """Send the question and retrieved chunks to the LLM."""
    prompt = build_prompt(question, chunks)

    # Read the Gemini API key from the environment or a .env file.
    api_key = os.getenv("GEMINI_API_KEY")

    # Stop early with a clear message if the key is missing.
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    # Create the Gemini client with the user's API key.
    client = genai.Client(api_key=api_key)

    # Let users change the model in .env, while keeping a good default.
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Use a simple Gemini text generation request.
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="You answer questions using retrieved document context.",
            temperature=0.2,
        ),
    )

    # Return Gemini's answer text.
    return response.text


def answer_question(question):
    """Run the full RAG flow for one question."""
    # Retrieve the most relevant chunks from ChromaDB.
    chunks = retrieve_relevant_chunks(question)

    # Send the retrieved chunks and question to Gemini for the final answer.
    return ask_llm(question, chunks)


@api.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Answer a user question through the RAG chatbot."""
    # Remove extra spaces so empty messages can be rejected clearly.
    question = request.message.strip()

    # Return a friendly API error if the message is empty.
    if not question:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        # Run retrieval plus Gemini answer generation.
        answer = answer_question(question)

        # Return the answer in the required JSON shape.
        return ChatResponse(reply=answer)

    except Exception as error:
        # Convert setup or runtime problems into a clear API error response.
        raise HTTPException(status_code=500, detail=str(error)) from error


def chat_loop():
    """Run the terminal chatbot."""
    print("SkyGrid RAG Chatbot")
    print("Ask questions about your documents.")
    print("Type 'exit' or 'quit' to stop.\n")

    # Keep asking for questions until the user exits.
    while True:
        question = input("You: ").strip()

        # Empty input should not call the retriever or LLM.
        if not question:
            continue

        # Let the user end the chat naturally.
        if question.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        try:
            # Run the same RAG flow used by the FastAPI endpoint.
            answer = answer_question(question)

            print(f"\nSkyGrid: {answer}\n")

        except Exception as error:
            # Show a beginner-friendly message for setup or runtime problems.
            print("\nSomething went wrong.")
            print("Make sure you ran: python ingest.py")
            print("Make sure GEMINI_API_KEY is set in your environment or .env file.")
            print(f"Error details: {error}\n")


if __name__ == "__main__":
    # Running this file directly starts the chatbot.
    chat_loop()
