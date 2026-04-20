# Gemini Setup - Complete

## ✅ Gemini Scripts Ready!

Аналогичная структура к Codex теперь готова для Google Gemini.

## 📁 Structure

```
scripts/ai/gemini/
├── run-gemini.ps1 ⭐           Main entry point (PowerShell)
├── run-gemini.sh ⭐            Main entry point (Bash)
├── .env.gemini                API key config
├── helper/
│   ├── check-env.ps1          Environment check (PS)
│   ├── check-env.sh           Environment check (Bash)
│   ├── setup-env.sh           Setup components
│   └── run-gemini-impl.sh     Gemini launcher
└── README.md                  Full guide
```

## 🚀 Quick Start

### PowerShell

```powershell
cd scripts/ai/gemini

# Get API key from: https://aistudio.google.com/app/apikeys
notepad .env.gemini

# Run Gemini
.\run-gemini.ps1
.\run-gemini.ps1 "what is AI?"
```

### WSL/Bash

```bash
cd scripts/ai/gemini

# Get API key from: https://aistudio.google.com/app/apikeys
nano .env.gemini

# Run Gemini
bash run-gemini.sh
bash run-gemini.sh "what is AI?"
```

## 📋 Commands

```
.\run-gemini.ps1 help              Show help
.\run-gemini.ps1                   Interactive
.\run-gemini.ps1 "prompt"          With prompt
.\run-gemini.ps1 check             Check setup
.\run-gemini.ps1 setup             Setup components
```

## 🔐 API Key

1. Go to: https://aistudio.google.com/app/apikeys
2. Sign in with Google
3. Click "Create API Key"
4. Copy the key (AIzaSy...)
5. Edit `.env.gemini` and paste it

## ✨ Features

✅ Single entry point (run-gemini.ps1 or run-gemini.sh)
✅ Automatic environment checks
✅ Auto-installs Python3, pip3, google-generativeai
✅ Clear status messages
✅ Interactive and prompt modes
✅ Works on first run
✅ Portable inside the repository

## 🎓 How It Works

```
User runs: .\run-gemini.ps1
    ↓
Check environment
    ↓
Components OK? → YES → Launch Gemini
         ↓
         NO
         ↓
Run setup (install Python, pip, package)
         ↓
Launch Gemini
```

## 📝 Configuration

Edit `.env.gemini`:

```
GEMINI_API_KEY=AIzaSy...
```

## ✅ Ready!

```powershell
cd scripts/ai/gemini
.\run-gemini.ps1
```

Gemini will:
1. Check environment
2. Setup if needed
3. Launch automatically

---

**Comparison: Codex vs Gemini**

| Feature | Codex | Gemini |
|---------|-------|--------|
| Model | GPT (OpenAI) | Gemini (Google) |
| Language | bash/Node.js | Python |
| Setup | Codex CLI npm | google-generativeai pip |
| Config | OPENAI_API_KEY | GEMINI_API_KEY |
| API Key | https://platform.openai.com | https://aistudio.google.com |
| Both use | Same structure | Same structure |

---

**Both ready to use!**

- `scripts/ai/codex/run-codex.ps1`
- `scripts/ai/gemini/run-gemini.ps1`

🚀
