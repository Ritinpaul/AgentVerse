import os
import sys
import time
import json
from threading import Event

# Add the SDK to path so we can import it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk', 'python')))

from nuuvixx.agent import listen, send_message

def test_a2a_communication():
    print("Testing A2A Communication (WebSockets + Redis Pub/Sub)")
    print("=====================================================")
    
    # We will simulate a "Manager" agent and a "Worker" agent.
    manager_id = "manager-alpha"
    worker_id = "worker-beta"
    
    # 1. Start the worker listening for messages
    message_received_event = Event()
    received_data = {}
    
    def worker_callback(message: dict):
        print(f"\n[Worker] Received message: {json.dumps(message, indent=2)}")
        received_data.update(message)
        message_received_event.set()
        
    print(f"\n1. Starting listener for {worker_id}...")
    listener_thread = listen(agent_id=worker_id, callback=worker_callback)
    
    # Wait a tiny bit for the websocket connection to establish
    time.sleep(1)
    
    # 2. Manager sends a message to the worker
    print(f"\n2. Manager ({manager_id}) sending task to Worker ({worker_id})...")
    success = send_message(
        target_agent_id=worker_id,
        content="Please analyze the latest log files.",
        sender_id=manager_id,
        metadata={"priority": "high", "task_type": "analysis"}
    )
    
    if not success:
        print("Failed to send message via State Plane.")
        sys.exit(1)
        
    # 3. Wait for the worker to receive the message
    print("\n3. Waiting for worker to receive message...")
    got_message = message_received_event.wait(timeout=5.0)
    
    if got_message:
        print("\n[SUCCESS] A2A Communication Successful!")
        print(f"Content verified: {received_data['content'] == 'Please analyze the latest log files.'}")
    else:
        print("\n[ERROR] Timed out waiting for message. Pub/Sub or WebSocket failed.")
        sys.exit(1)

if __name__ == "__main__":
    test_a2a_communication()
