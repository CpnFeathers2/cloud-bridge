import json
import os
import datetime
import subprocess
import sys

MESSAGE_FILE = 'bridge/message.json'

def run_git_command(command):
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def pull_updates():
    # print("Checking for new messages...") # Commented out to reduce noise
    return run_git_command(['git', 'pull'])

def push_updates(commit_message):
    print("Sending message...")
    if not run_git_command(['git', 'add', MESSAGE_FILE]):
        print("Error adding file.")
        return False
    if not run_git_command(['git', 'commit', '-m', commit_message]):
        print("Error committing.")
        return False
    if not run_git_command(['git', 'push']):
        print("Error pushing. Pulling changes and retrying...")
        if not pull_updates():
            print("Failed to pull updates.")
            return False
        if not run_git_command(['git', 'push']):
             print("Failed to push.")
             return False
    return True

def load_messages():
    if not os.path.exists(MESSAGE_FILE):
        return []
    with open(MESSAGE_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_message(sender, content):
    messages = load_messages()
    new_message = {
        'sender': sender,
        'timestamp': datetime.datetime.now().isoformat(),
        'content': content
    }
    messages.append(new_message)
    with open(MESSAGE_FILE, 'w') as f:
        json.dump(messages, f, indent=2)
    return new_message

def display_messages(messages):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=== PROJECT CHAT ===")
    for msg in messages:
        timestamp = msg.get('timestamp', '')
        sender = msg.get('sender', 'Unknown')
        content = msg.get('content', '')
        # Simple formatting
        print(f"[{timestamp}] {sender}: {content}")
    print("====================")
    print("(Type a message and press Enter to send. Press Enter to refresh. Type 'exit' to quit.)")

def main():
    print("Welcome to Cloud Bridge Chat")
    sender_name = input("Enter your name: ").strip()
    if not sender_name:
        sender_name = "User"

    while True:
        pull_updates()
        messages = load_messages()
        display_messages(messages)

        try:
            content = input(f"\n[{sender_name}] > ")
        except EOFError:
            break

        if content.lower() == 'exit':
            break
        elif content == '':
            continue
        else:
            save_message(sender_name, content)
            push_updates(f"Message from {sender_name}")

if __name__ == "__main__":
    main()
