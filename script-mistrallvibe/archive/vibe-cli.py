#!/usr/bin/env python3
"""
Mistral Vibe - Interactive Chat CLI
Usage: python vibe-cli.py [model]
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import requests
from typing import Optional
from datetime import datetime


class VibeAPIError(RuntimeError):
    """Raised when the Mistral Vibe API request cannot be completed."""


class MistralVibeCLI:
    """Interactive chat interface for Mistral API"""

    MODELS = {
        'small': 'mistral-small-latest',
        'medium': 'mistral-medium-latest',
        'large': 'mistral-large-latest',
    }

    def __init__(self, api_key: Optional[str] = None, model: str = 'small'):
        """Initialize CLI"""
        self.api_key = api_key or os.environ.get('VIBE_API_KEY')
        if not self.api_key:
            raise ValueError("VIBE_API_KEY not set. Set it in environment or .env.mistrallvibe")

        self.model = self.MODELS.get(model, model)
        self.base_url = "https://api.mistral.ai/v1"
        self.conversation = []
        self.session_start = datetime.now()

    def send_message(self, message: str) -> str:
        """Send message to Mistral API and get response"""
        self.conversation.append({
            'role': 'user',
            'content': message
        })

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': self.conversation,
                    'temperature': 0.7,
                    'max_tokens': 1024,
                    'top_p': 1.0
                },
                timeout=30
            )

            if response.status_code != 200:
                error = response.json().get('error', {})
                raise VibeAPIError(f"API Error: {error.get('message', 'Unknown error')}")

            data = response.json()
            assistant_message = data['choices'][0]['message']['content']

            self.conversation.append({
                'role': 'assistant',
                'content': assistant_message
            })

            return assistant_message

        except requests.exceptions.RequestException as e:
            raise VibeAPIError(f"Request failed: {e}") from e

    def print_welcome(self):
        """Print welcome message"""
        print("\n" + "=" * 60)
        print("  🎯 Mistral Vibe - Interactive Chat CLI")
        print("=" * 60)
        print(f"  Model: {self.model}")
        print("  Type 'help' for commands, 'exit' to quit")
        print("=" * 60 + "\n")

    def print_help(self):
        """Print help message"""
        print("\n" + "-" * 60)
        print("Commands:")
        print("  help          Show this help message")
        print("  model         Show current model")
        print("  models        List available models")
        print("  switch <m>    Switch model (small/medium/large)")
        print("  clear         Clear conversation history")
        print("  info          Show conversation info")
        print("  exit/quit     Exit the chat")
        print("-" * 60 + "\n")

    def print_models(self):
        """Print available models"""
        print("\nAvailable models:")
        for name, full_name in self.MODELS.items():
            marker = "✓" if self.model == full_name else " "
            print(f"  [{marker}] {name:10} - {full_name}")
        print()

    def switch_model(self, model_name: str):
        """Switch to different model"""
        if model_name.lower() not in self.MODELS:
            print(f"Unknown model: {model_name}")
            print(f"Available: {', '.join(self.MODELS.keys())}")
            return

        self.model = self.MODELS[model_name.lower()]
        self.conversation = []  # Clear history on model switch
        print(f"\n✓ Switched to {model_name} model (conversation cleared)\n")

    def print_info(self):
        """Print conversation info"""
        elapsed = datetime.now() - self.session_start
        print("\nConversation Info:")
        print(f"  Model: {self.model}")
        print(f"  Messages: {len(self.conversation)}")
        print(f"  Duration: {elapsed.total_seconds():.1f}s")
        if self.conversation:
            tokens_estimate = sum(len(msg['content'].split()) for msg in self.conversation)
            print(f"  Estimated tokens: ~{tokens_estimate * 1.3:.0f}")
        print()

    def _handle_command(self, user_input: str) -> str | None:
        """Handle built-in commands and return an action marker when matched."""
        normalized = user_input.lower()

        if normalized in {'exit', 'quit'}:
            print("\nGoodbye! 👋\n")
            return 'exit'

        if normalized == 'help':
            self.print_help()
            return 'handled'

        if normalized == 'models':
            self.print_models()
            return 'handled'

        if normalized == 'model':
            print(f"\nCurrent model: {self.model}\n")
            return 'handled'

        if normalized == 'clear':
            self.conversation = []
            print("\n✓ Conversation cleared\n")
            return 'handled'

        if normalized == 'info':
            self.print_info()
            return 'handled'

        if normalized.startswith('switch '):
            self.switch_model(user_input[7:].strip())
            return 'handled'

        return None

    def run(self):
        """Run interactive chat loop"""
        self.print_welcome()

        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue

                action = self._handle_command(user_input)
                if action == 'exit':
                    break
                if action == 'handled':
                    continue

                print("\nMistral: ", end="", flush=True)
                response = self.send_message(user_input)
                print(response)
                print()

            except KeyboardInterrupt:
                print("\n\nChat interrupted. Type 'exit' to quit or continue chatting.\n")
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point"""
    model = 'small'
    if len(sys.argv) > 1:
        model = sys.argv[1].lower()

    try:
        cli = MistralVibeCLI(model=model)
        cli.run()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)


if __name__ == '__main__':
    main()
