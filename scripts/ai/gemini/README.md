# Gemini - Local Launcher

Автономная точка входа для запуска Google Gemini AI из `scripts/ai/gemini`.

## 📁 Структура

```
scripts/ai/gemini/
├── run-gemini.ps1             ⭐ Main entry point (PowerShell)
├── run-gemini.sh              ⭐ Main entry point (WSL/Bash)
├── .env.gemini                # API key configuration
├── helper/                    # Helper scripts
│   ├── check-env.ps1          # Check environment (PowerShell)
│   ├── check-env.sh           # Check environment (Bash)
│   ├── setup-env.sh           # Setup missing components
│   └── run-gemini-impl.sh     # Gemini launcher implementation
├── README.md                  # This file
└── docs/                      # Documentation
```

## 🚀 Quick Start

### From PowerShell (Windows)

```powershell
cd scripts/ai/gemini

# First time: check and setup
.\run-gemini.ps1 check
.\run-gemini.ps1 setup

# Edit API key
notepad .env.gemini

# Run Gemini
.\run-gemini.ps1
.\run-gemini.ps1 "what is AI?"
```

### From WSL (Ubuntu)

```bash
cd scripts/ai/gemini

# First time: check and setup
bash run-gemini.sh check
bash run-gemini.sh setup

# Edit API key
nano .env.gemini

# Run Gemini
bash run-gemini.sh
bash run-gemini.sh "what is AI?"
```

## 📋 Commands

```powershell
# PowerShell
.\run-gemini.ps1 help              # Show help
.\run-gemini.ps1                   # Interactive mode
.\run-gemini.ps1 "prompt"          # With prompt
.\run-gemini.ps1 check             # Check setup
.\run-gemini.ps1 setup             # Install missing components
```

```bash
# WSL/Bash
bash run-gemini.sh help            # Show help
bash run-gemini.sh                 # Interactive mode
bash run-gemini.sh "prompt"        # With prompt
bash run-gemini.sh check           # Check setup
bash run-gemini.sh setup           # Install missing components
```

## 🔧 What run-gemini does

1. **Check environment** - Validates WSL, Python3, pip3, google-generativeai package
2. **Setup if needed** - Auto-installs missing components (Python, pip, package)
3. **Verify API key** - Ensures .env.gemini has valid Google API key
4. **Launch Gemini** - Runs Gemini with proper environment setup

## ⚙️ Setup

### 1. Get Google API Key

1. Go to: https://aistudio.google.com/app/apikeys
2. Click "Create API Key"
3. Copy the key

### 2. Edit .env.gemini

```powershell
notepad .env.gemini
```

Or:

```bash
nano .env.gemini
```

Add your API key:

```
GEMINI_API_KEY=your-api-key-here
```

### 3. First Run

```powershell
.\run-gemini.ps1
```

This will:
- Check all dependencies
- Install missing components (if any)
- Launch Gemini

## 📚 Helper Scripts

All logic is in `helper/` folder:

- `check-env.ps1` / `check-env.sh` - Verify setup
- `setup-env.sh` - Install components (Python, pip, Google GenAI SDK)
- `run-gemini-impl.sh` - Launch Gemini with environment

## 🔐 API Key

Get from: https://aistudio.google.com/app/apikeys

1. Sign in with Google account
2. Click "Create API Key"
3. Copy the key (looks like: AIzaSy...)
4. Paste into `.env.gemini`

## 🐧 Requirements

- Windows 11 + WSL2
- Ubuntu in WSL
- Internet connection
- Google account (for API key)

Python3 and pip3 are auto-installed if missing.

Жёсткие пути вида `/mnt/e/...` не используются: PowerShell launcher вычисляет
WSL-путь от текущего расположения репозитория, а Bash helper'ы определяют
корень через `git rev-parse` с локальным fallback.

## 🆘 Troubleshooting

### "API key not found"

```powershell
notepad .env.gemini
```

Make sure you have `GEMINI_API_KEY=AIzaSy...` with valid key.

### "Python3 not found"

Run setup:
```powershell
.\run-gemini.ps1 setup
```

### "Gemini Python SDK not installed"

Run setup:
```powershell
.\run-gemini.ps1 setup
```

### Check what's wrong

```powershell
.\run-gemini.ps1 check
```

## 📝 Files

- `run-gemini.ps1` - Main entry point (PowerShell)
- `run-gemini.sh` - Main entry point (Bash)
- `.env.gemini` - API key configuration
- `helper/` - All helper scripts

## ✅ Ready!

Just run:

```powershell
.\run-gemini.ps1
```

Gemini will check, setup if needed, and launch! 🚀

## 💻 Interactive Mode

Type your questions:

```
>>> what is quantum computing?
[Response from Gemini]

>>> explain machine learning
[Response from Gemini]

>>> exit
```

Type `exit` or `quit` to exit.

## 🎯 Examples

```powershell
# Ask a question directly
.\run-gemini.ps1 "what is AI?"

# Interactive conversation
.\run-gemini.ps1

# Multi-word prompt
.\run-gemini.ps1 "explain the theory of relativity in simple terms"
```

---

**Status**: ✅ Ready to use!

Get API key: https://aistudio.google.com/app/apikeys

Then run: `.\run-gemini.ps1`
