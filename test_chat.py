import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
import subprocess
import chat

class TestChat(unittest.TestCase):

    @patch('chat.os.path.exists')
    def test_load_messages_no_file(self, mock_exists):
        mock_exists.return_value = False
        messages = chat.load_messages()
        self.assertEqual(messages, [])

    @patch('chat.os.path.exists')
    def test_load_messages_valid(self, mock_exists):
        mock_exists.return_value = True
        read_data = json.dumps([{"sender": "User", "content": "Hello"}])
        with patch('builtins.open', mock_open(read_data=read_data)):
             messages = chat.load_messages()
             self.assertEqual(len(messages), 1)
             self.assertEqual(messages[0]['sender'], "User")
             self.assertEqual(messages[0]['content'], "Hello")

    @patch('chat.load_messages')
    @patch('json.dump')
    def test_save_message(self, mock_json_dump, mock_load):
        mock_load.return_value = []
        with patch('builtins.open', mock_open()) as mock_file:
            new_msg = chat.save_message("User", "New message")

            self.assertEqual(new_msg['sender'], "User")
            self.assertEqual(new_msg['content'], "New message")

            # Check if json.dump was called with the correct list
            mock_json_dump.assert_called_once()
            args, _ = mock_json_dump.call_args
            # args[0] is the list of messages
            self.assertEqual(len(args[0]), 1)
            self.assertEqual(args[0][0]['content'], "New message")

    @patch('chat.subprocess.run')
    def test_run_git_command_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = chat.run_git_command(['git', 'status'])
        self.assertTrue(result)
        mock_run.assert_called_with(['git', 'status'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @patch('chat.subprocess.run')
    def test_run_git_command_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd')
        result = chat.run_git_command(['git', 'invalid'])
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
