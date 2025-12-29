import os
import uuid
import datetime
import tempfile
import base64
import binascii
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import speech_recognition as sr
import pyttsx3
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from groq import Groq

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to the specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount captures directory
if not os.path.exists("captures"):
    os.makedirs("captures")
app.mount("/captures", StaticFiles(directory="captures"), name="captures")

# Initialize Groq Client for direct API calls (like STT)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Models
class AIReplyRequest(BaseModel):
    sessionId: str
    message: str

class TTSRequest(BaseModel):
    text: str

class OwnerReplyRequest(BaseModel):
    sessionId: str
    message: str
    isVoice: bool = False

class CaptureRequest(BaseModel):
    image: Optional[str] = None

# Smart Doorbell Logic
class SmartDoorbell:
    def __init__(self, api_key: str):
        self.llm = ChatGroq(
            temperature=0.7,
            groq_api_key=api_key,
            model_name="llama-3.3-70b-versatile"
        )
        
        self.system_prompt = SystemMessage(content=(
            "You are a Smart Doorbell for the 'Kandell' residence. "
            "Handle visitors politely and briefly (1-2 sentences).\n"
            "- If they are a DELIVERY PERSON: Ask them to leave the package in the 'Parcel Box' to the left.\n"
            "- If they are a FRIEND/FAMILY: Tell them you are notifying the owner now.\n"
            "- If they are a SOLICITOR: Politely mention the 'No Soliciting' policy.\n"
            "- If they are a NEIGHBOR: Be friendly and ask if it is urgent.\n"
            "Always ask for their name and purpose if not provided."
        ))
        
        self.sessions = {}
        self.logs = []
        self.recognizer = sr.Recognizer()

    def speak(self, text: str):
        print(f"Doorbell (Voice): {text}")
        try:
            # Initialize engine in the call to avoid thread issues
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.say(text)
            engine.runAndWait()
            # Explicitly delete engine to free resources
            del engine
        except Exception as e:
            print(f"Error in TTS: {e}")

    def _get_session_history(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = [self.system_prompt]
        return self.sessions[session_id]

    def get_response(self, visitor_input: str, session_id: str, image_url: Optional[str] = None):
        history = self._get_session_history(session_id)
        history.append(HumanMessage(content=visitor_input))
        
        try:
            response = self.llm.invoke(history)
            history.append(response)
            
            # Update logs
            self._update_logs(session_id, visitor_input, response.content, image_url)
            
            return response.content
        except Exception as e:
            return f"Error: {str(e)}"

    def _update_logs(self, session_id: str, visitor_msg: str, ai_reply: str, image_url: Optional[str] = None):
        # Find or create log entry
        log_entry = next((l for l in self.logs if l['id'] == session_id), None)
        if not log_entry:
            log_entry = {
                "id": session_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "imageUrl": image_url or "/placeholder.svg",
                "transcript": [],
                "status": "active",
                "aiSummary": "Visitor interaction",
                "visitorType": "unknown"
            }
            self.logs.append(log_entry)
        
        log_entry["transcript"].append({
            "role": "visitor",
            "content": visitor_msg,
            "timestamp": datetime.datetime.now().isoformat()
        })
        log_entry["transcript"].append({
            "role": "doorbell",
            "content": ai_reply,
            "timestamp": datetime.datetime.now().isoformat()
        })

# Initialize Doorbell
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("Warning: GROQ_API_KEY not found in .env")
doorbell = SmartDoorbell(api_key or "")

@app.post("/ring")
async def ring(request: CaptureRequest = CaptureRequest(image=None)):
    session_id = f"visitor_{uuid.uuid4().hex[:8]}"
    
    image_url = None
    if request.image:
        try:
            # Image comes as "data:image/jpeg;base64,..."
            if "," in request.image:
                header, encoded = request.image.split(",", 1)
            else:
                encoded = request.image
                
            data = base64.b64decode(encoded)
            filename = f"capture_{uuid.uuid4().hex}.jpg"
            filepath = os.path.join("captures", filename)
            
            with open(filepath, "wb") as f:
                f.write(data)
                
            image_url = f"/captures/{filename}"
        except Exception as e:
            print(f"Error saving ring image: {e}")

    greeting = doorbell.get_response("The doorbell button was pressed.", session_id, image_url=image_url)
    return {"sessionId": session_id, "greeting": greeting, "imageUrl": image_url}

@app.post("/ai-reply")
async def ai_reply(request: AIReplyRequest):
    reply = doorbell.get_response(request.message, request.sessionId)
    return {
        "reply": reply,
        "summary": "Visitor interaction",
        "visitorType": "unknown"
    }

@app.post("/tts")
async def tts(request: TTSRequest):
    doorbell.speak(request.text)
    return {"status": "success"}

@app.post("/capture-image")
async def capture_image(request: CaptureRequest):
    if request.image:
        try:
            # Image comes as "data:image/jpeg;base64,..."
            # Check if header exists
            if "," in request.image:
                header, encoded = request.image.split(",", 1)
            else:
                encoded = request.image
                
            data = base64.b64decode(encoded)
            
            filename = f"capture_{uuid.uuid4().hex}.jpg"
            filepath = os.path.join("captures", filename)
            
            with open(filepath, "wb") as f:
                f.write(data)
                
            image_url = f"/captures/{filename}"
            return {"imageUrl": image_url}
            
        except Exception as e:
            print(f"Error saving image: {e}")
            return {"imageUrl": "/placeholder.svg"}
            
    return {"imageUrl": "/placeholder.svg"}

@app.post("/stt")
async def stt(audio: UploadFile = File(...)):
    temp_audio_path = None
    try:
        # Create a temporary file to store the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            import shutil
            shutil.copyfileobj(audio.file, temp_audio)
            temp_audio_path = temp_audio.name
        
        file_size = os.path.getsize(temp_audio_path)
        print(f"Received audio file: {audio.filename}, size: {file_size} bytes")
        
        # Groq Whisper needs a minimum file size/duration
        if file_size < 100:
            raise HTTPException(status_code=400, detail="Audio file too small. Please speak longer.")

        try:
            # Use Groq Whisper for transcription
            print(f"Sending to Groq Whisper: {temp_audio_path}")
            with open(temp_audio_path, "rb") as audio_file:
                # Ensure we have a valid filename for Groq
                fname = audio.filename if audio.filename and audio.filename != "blob" else "audio.webm"
                if not fname.endswith(('.webm', '.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.ogg')):
                    fname += ".webm"
                
                transcription = groq_client.audio.transcriptions.create(
                    file=(fname, audio_file),
                    model="whisper-large-v3",
                )
            print(f"Transcription successful: {transcription.text}")
            return {"text": transcription.text}
        except Exception as groq_err:
            print(f"Groq STT Error: {groq_err}")
            # If it's a Groq API error, try to extract details
            detail = str(groq_err)
            status_code = 500
            if hasattr(groq_err, 'status_code'):
                status_code = groq_err.status_code
            raise HTTPException(status_code=status_code, detail=detail)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"STT Endpoint Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except:
                pass

@app.get("/logs")
async def get_logs():
    return doorbell.logs

@app.post("/owner-reply")
async def owner_reply(request: OwnerReplyRequest):
    # If it's a voice reply, play it on the doorbell
    if request.isVoice:
        doorbell.speak(request.message)
    
    # Update transcript in logs
    log_entry = next((l for l in doorbell.logs if l['id'] == request.sessionId), None)
    if log_entry:
        log_entry["transcript"].append({
            "role": "doorbell",
            "content": f"[Owner]: {request.message}",
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
