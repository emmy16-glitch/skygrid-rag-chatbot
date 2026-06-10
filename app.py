import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
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
            "whatsapp_webhook": "/webhook",
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


def extract_whatsapp_text(payload):
    """Extract the sender phone number and text from a WhatsApp webhook payload."""
    try:
        # WhatsApp sends webhook events inside entry -> changes -> value.
        value = payload["entry"][0]["changes"][0]["value"]

        # Ignore status callbacks because they do not contain user messages.
        messages = value.get("messages", [])
        if not messages:
            return None, None

        # This beginner version handles the first incoming message only.
        message = messages[0]

        # The sender's WhatsApp ID is needed so we can send the reply back.
        sender_phone_number = message.get("from")

        # Only text messages have a text.body field.
        text = message.get("text", {}).get("body", "")

        return sender_phone_number, text.strip()

    except (KeyError, IndexError, TypeError):
        # If Meta sends a shape we do not understand, treat it as no message.
        return None, None


def send_whatsapp_message(to_phone_number, reply_text):
    """Send the chatbot reply back to the user through WhatsApp Cloud API."""
    # Read WhatsApp settings from environment variables.
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    # Stop with a clear error if deployment variables are missing.
    if not access_token:
        raise ValueError("WHATSAPP_ACCESS_TOKEN is not set.")
    if not phone_number_id:
        raise ValueError("WHATSAPP_PHONE_NUMBER_ID is not set.")

    # The API version can be changed without editing code if Meta updates it.
    api_version = os.getenv("WHATSAPP_API_VERSION", "v20.0")

    # This is the WhatsApp Cloud API endpoint for sending messages.
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

    # Meta expects a bearer token for authorization.
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # This sends a simple text reply to the same WhatsApp user.
    data = {
        "messaging_product": "whatsapp",
        "to": to_phone_number,
        "type": "text",
        "text": {"body": reply_text},
    }

    # Make the HTTP request to Meta's Graph API.
    response = httpx.post(url, headers=headers, json=data, timeout=30)

    # Raise an error if Meta rejects the request.
    response.raise_for_status()

    return response.json()


@api.get("/webhook", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    mode: str = Query(default="", alias="hub.mode"),
    token: str = Query(default="", alias="hub.verify_token"),
    challenge: str = Query(default="", alias="hub.challenge"),
):
    """Verify the webhook URL when setting it up in Meta."""
    # Meta sends hub.mode=subscribe when verifying a webhook.
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    # The token from Meta must match the token in our environment variables.
    if mode == "subscribe" and token == expected_token:
        return challenge

    # Return 403 if the verify token is missing or incorrect.
    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@api.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """Receive WhatsApp messages, answer with RAG, and send the reply back."""
    # Read the raw webhook JSON sent by Meta.
    payload = await request.json()

    # Pull the sender phone number and message text out of Meta's nested payload.
    sender_phone_number, user_message = extract_whatsapp_text(payload)

    # Some webhook events are delivery statuses, not user messages.
    if not sender_phone_number or not user_message:
        return {"status": "ignored"}

    try:
        # Reuse the same RAG function used by /chat.
        chatbot_reply = answer_question(user_message)

        # Send the chatbot answer back to the WhatsApp user.
        send_whatsapp_message(sender_phone_number, chatbot_reply)

        return {"status": "sent"}

    except Exception as error:
        # Return a clear API error if Gemini, ChromaDB, or WhatsApp fails.
        raise HTTPException(status_code=500, detail=str(error)) from error


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
