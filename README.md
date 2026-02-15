# cloud-bridge

This repository facilitates bridging data between cloud environments and local machines (e.g., Windows, Oracle AI).

## Directory Structure

- `bridge/`: Contains files for communication.
  - `cmd.json`: Command file.
  - `result.json`: Result file.
  - `message.json`: Message file for external readers.

## Usage

### Chat Interface

A simple chat interface is provided to communicate between connected machines (Windows, Oracle, Cloud) using Git as the transport layer.

1.  **Prerequisites:**
    -   Python 3 installed.
    -   Git configured and initialized in the repository.

2.  **Running the Chat:**
    -   Run the `chat.py` script:
        ```bash
        python3 chat.py
        ```
    -   Enter your name when prompted.
    -   Type messages and press Enter to send.
    -   Press Enter on an empty line to refresh messages from the repository.
    -   Type `exit` to quit.

The script automatically pulls the latest changes before displaying messages and pushes your new messages after you send them.
