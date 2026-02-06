import urllib.request
import json
import time

BASE_URL = "http://localhost:8000/chat"
SESSION_ID = "demo_verification_user"

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
            print(f"\nUser: {message}")
            print(f"Doctor AI: {result['reply']}")
            if "state" in result:
                 s = result["state"]
                 print(f"DEBUG STATE: has_prior_pregnancies={s.get('has_prior_pregnancies')}, ivf_done={s.get('treatments',{}).get('ivf',{}).get('done')}")
            return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def run_flow():
    print("Starting Headless Verification Flow...")
    
    # 1. Start
    send_message("Hi")
    time.sleep(0.5)
    
    # 2. Ages
    send_message("I am 32 and partner is 34")
    time.sleep(0.5)
    
    # 3. Duration
    send_message("Trying for 2 years")
    time.sleep(0.5)
    
    # 4. Pregnancy
    send_message("No prior pregnancies")
    time.sleep(0.5)
    
    # 5. Treatments
    send_message("No treatments done")
    time.sleep(0.5)
    
    # 6. Tests
    send_message("No tests yet")
    time.sleep(0.5)
    
    # 7. Reports
    last_response = send_message("No reports available")
    
    if last_response and "state" in last_response:
        print("\n\n--- FINAL GENERATED STATE ---")
        print(json.dumps(last_response["state"], indent=2))
        print("-----------------------------")

if __name__ == "__main__":
    run_flow()
