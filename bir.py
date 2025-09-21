from fastapi import FastAPI
from pydantic import BaseModel
import json, os
from datetime import datetime
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
import uuid
from typing import Optional

app = FastAPI(title="AI Doorbell Assistant")
sessions = {}

# ===============================
# Groq API setup (SAME as not.py)
# ===============================
llm = ChatGroq(
    temperature=0,
    groq_api_key="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",
    model_name="meta-llama/llama-4-scout-17b-16e-instruct"
)

# ===============================
# Memory + Prompt + Chain
# ===============================
memory = ConversationBufferMemory(return_messages=True)

prompt = PromptTemplate(
    input_variables=["history", "visitor_message"],
    template="""
You are a **safe AI doorbell assistant**.
- You cannot assume or reveal any information about people inside the house.
- You cannot perform any dangerous actions.
- Respond politely and concisely to the visitor.

Conversation history:
{history}

Visitor says: {visitor_message}
Provide a short, polite response.
"""
)

conversation_chain = LLMChain(
    llm=llm,
    prompt=prompt,
    memory=memory
)

# ===============================
# Dangerous request detection
# ===============================
DANGEROUS_KEYWORDS = [
    "unlock the door",
    "open the door",
    "disable alarm",
    "turn off security",
    "let me in",
    "give me access"
]

def is_dangerous(message: str) -> bool:
    return any(keyword in message.lower() for keyword in DANGEROUS_KEYWORDS)

# ===============================
# Conversation Logging
# ===============================
LOG_FILE = "doorbell_chat_log.json"

def log_conversation(visitor_message, bell_reply, dangerous=False, owner_reply=None):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "visitor_message": visitor_message,
        "bell_reply": bell_reply,
        "dangerous": dangerous,
        "owner_reply": owner_reply
    }
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    else:
        data = []
    data.append(log_entry)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===============================
# Models
# ===============================
class VisitorMessage(BaseModel):
    text: str
    session_id: Optional[str] = None

class OwnerMessage(BaseModel):
    text: str

# ===============================
# Routes
# ===============================
@app.post("/receive")
def receive_message(visitor: VisitorMessage):
    session_id = visitor.session_id or str(uuid.uuid4())
    memory = sessions.get(session_id)
    if memory is None:
        memory = ConversationBufferMemory(return_messages=True)
        sessions[session_id] = memory

    conversation_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        memory=memory
    )

    print("🔑 API KEY being used:", llm.groq_api_key)
    print("📩 Visitor message:", visitor.text)
    if is_dangerous(visitor.text):
        reply = "⚠️ Sorry, I cannot perform that action. The owner has been notified."
        log_conversation(visitor.text, reply, dangerous=True)
        return {"reply": reply, "dangerous": True, "session_id": session_id}
    
    reply = conversation_chain.run(visitor_message=visitor.text)
    log_conversation(visitor.text, reply, dangerous=False)
    return {"reply": reply, "dangerous": False, "session_id": session_id}

@app.post("/bell-conversation")
def owner_reply(owner: OwnerMessage):
    log_conversation(visitor_message="", bell_reply="", dangerous=False, owner_reply=owner.text)
    return {"owner_reply": owner.text}

@app.get("/danger-notify")
def danger_notify():
    if not os.path.exists(LOG_FILE):
        return {"dangerous_logs": []}
    with open(LOG_FILE, "r") as f:
        data = json.load(f)
    dangerous_logs = [entry for entry in data if entry["dangerous"]]
    return {"dangerous_logs": dangerous_logs}

@app.get("/current-message")
def get_current_message():
    if not os.path.exists(LOG_FILE):
        return {"message": "No messages yet."}
    with open(LOG_FILE, "r") as f:
        data = json.load(f)
    if not data:
        return {"message": "No messages yet."}
    last_message = data[-1]["visitor_message"]
    return {"message": last_message}
