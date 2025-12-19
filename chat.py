import os
import speech_recognition as sr
import pyttsx3
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables from .env
load_dotenv()

class SmartDoorbell:
    def __init__(self, api_key: str):
        """
        Initializes the Smart Doorbell with voice and session management.
        """
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
        
        # Initialize Speech Recognizer
        self.recognizer = sr.Recognizer()

    def speak(self, text: str):
        """
        Converts text to speech. Initializing here can be more reliable on some systems.
        """
        print(f"Doorbell (Voice): {text}")
        try:
            engine = pyttsx3.init('sapi5')
            engine.setProperty('rate', 150)
            voices = engine.getProperty('voices')
            if voices:
                # Defaulting to the first available voice
                engine.setProperty('voice', voices[0].id)
            
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"Error in TTS: {e}")
            # Fallback to default driver
            try:
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
            except:
                print("TTS failed completely.")

    def listen(self):
        """
        Listens for visitor speech and returns it as text.
        """
        with sr.Microphone() as source:
            print("\n[Listening...] (Speak now)")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("[Processing voice...]")
                text = self.recognizer.recognize_google(audio)
                print(f"Visitor (Voice): {text}")
                return text
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                print("Could not understand audio.")
                return None
            except sr.RequestError as e:
                print(f"Speech recognition error: {e}")
                return None

    def _get_session_history(self, session_id: str):
        """
        Retrieves or initializes chat history for a given session.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = [self.system_prompt]
        return self.sessions[session_id]

    def get_response(self, visitor_input: str, session_id: str = "default"):
        """
        Processes visitor speech for a specific session and returns the response.
        """
        history = self._get_session_history(session_id)
        history.append(HumanMessage(content=visitor_input))
        
        try:
            response = self.llm.invoke(history)
            history.append(response)
            return response.content
        except Exception as e:
            return f"Error: {str(e)}"

def main():
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("Error: GROQ_API_KEY not found.")
        return

    doorbell = SmartDoorbell(api_key)
    
    print("--- 🔔 Smart Doorbell Online ---")
    print("Commands: 'new' (new visitor), 'exit' (quit), 'v' (use voice input)\n")
    
    current_visitor = "Visitor_1"
    print(f"--- Starting session for {current_visitor} ---")
    
    initial_greeting = doorbell.get_response("The doorbell button was pressed.", current_visitor)
    doorbell.speak(initial_greeting)

    while True:
        try:
            # We allow both text and voice trigger
            choice = input(f"\n[{current_visitor}] Type message or 'v' for voice (or 'new'/'exit'): ").strip()
            
            if choice.lower() in ["exit", "quit", "bye"]:
                doorbell.speak("Have a great day!")
                break
            
            if choice.lower() == "new":
                new_id = f"Visitor_{len(doorbell.sessions) + 1}"
                current_visitor = new_id
                print(f"\n--- Starting new session for {current_visitor} ---")
                greeting = doorbell.get_response("The doorbell button was pressed.", current_visitor)
                doorbell.speak(greeting)
                continue

            visitor_speech = None
            if choice.lower() == 'v':
                visitor_speech = doorbell.listen()
                if not visitor_speech:
                    print("No speech detected. Try again.")
                    continue
            else:
                visitor_speech = choice

            if not visitor_speech:
                continue
                
            response = doorbell.get_response(visitor_speech, current_visitor)
            doorbell.speak(response)
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
