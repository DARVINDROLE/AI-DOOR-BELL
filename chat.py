import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

class SmartDoorbell:
    def __init__(self, api_key: str):
        """
        Initializes the Smart Doorbell with a specific persona.
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
        
        self.chat_history = [self.system_prompt]

    def get_response(self, visitor_input: str):
        """
        Processes visitor speech and returns the doorbell's response.
        """
        self.chat_history.append(HumanMessage(content=visitor_input))
        try:
            response = self.llm.invoke(self.chat_history)
            self.chat_history.append(response)
            return response.content
        except Exception as e:
            return f"Error: {str(e)}"

def main():
    api_key = os.getenv("GROQ_API_KEY", "-----")
    
    if not api_key:
        print("Error: GROQ_API_KEY not found.")
        return

    doorbell = SmartDoorbell(api_key)
    
    print("--- 🔔 Smart Doorbell Online ---")
    print("(Type 'exit' to quit)\n")
    
    # Simulate first greeting
    print("Doorbell: " + doorbell.get_response("The doorbell button was pressed."))

    while True:
        try:
            visitor_speech = input("Visitor: ")
            if visitor_speech.lower() in ["exit", "quit", "bye"]:
                print("Doorbell: Have a great day!")
                break
                
            response = doorbell.get_response(visitor_speech)
            print(f"Doorbell: {response}")
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
