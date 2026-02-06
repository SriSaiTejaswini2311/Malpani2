import urllib.request
import json
import sys

import uuid

BASE_URL = "http://localhost:8000/chat"
SESSION_ID = f"manual_test_{uuid.uuid4().hex[:8]}"

def send_message(message):
    data = {
        "session_id": SESSION_ID,
        "message": message
    }
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None

def main():
    print("\n=== IVF Engine Manual Test CLI ===")
    print("Type 'quit' or 'exit' to stop.")
    print("Type 'state' to see the full current JSON state.")
    print("----------------------------------\n")

    # Initial greeting (handled by server if we send empty? No, checking flow)
    # Actually, usually user says "Hi" first.
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        
        if user_input.lower() == "state":
            # Hack/Trick: We can't just GET state without sending a message in this simple API 
            # unless we add a GET endpoint or send a dummy message.
            # But the LAST response had the state.
            print("  (State is returned with every reply. showing last known state not easy here without tracking)")
            print("  Just send a dummy message like '.' to get state if needed.")
            continue

        response = send_message(user_input)
        
        if response:
            print(f"Doctor AI: {response['reply']}")
            
            # Show key state updates for debugging
            state = response.get("state", {})
            print(f"\n  [DEBUG STATE]")
            print(f"  - Patient Age: {state.get('demographics',{}).get('patient_age')}")
            print(f"  - Partner Age: {state.get('demographics',{}).get('partner_age')}")
            print(f"  - Prior Pregnancies: {state.get('has_prior_pregnancies')}")
            # print(f"  - Full State: {json.dumps(state, indent=2)}") # Uncomment for full dump

if __name__ == "__main__":
    main()
