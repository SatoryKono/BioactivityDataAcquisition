# Codex vs Gemini - Side by Side

## ✅ Both AI Assistants Ready!

Теперь у вас есть две полностью подготовленные системы:

## 📦 Folder Structure

```
script-codex/                    script-gemini/
├── run-codex.ps1              ├── run-gemini.ps1
├── run-codex.sh               ├── run-gemini.sh
├── .env.codex                 ├── .env.gemini
├── helper/                    ├── helper/
│   ├── check-env.ps1          │   ├── check-env.ps1
│   ├── check-env.sh           │   ├── check-env.sh
│   ├── setup-env.sh           │   ├── setup-env.sh
│   └── run-codex-impl.sh      │   └── run-gemini-impl.sh
└── README.md                  └── README.md
```

## 📊 Comparison

| Aspect | Codex | Gemini |
|--------|-------|--------|
| **Provider** | OpenAI | Google |
| **AI Model** | GPT | Gemini |
| **Runtime** | Node.js + npm | Python + pip |
| **Package** | @openai/codex | google-generativeai |
| **API Key Source** | https://platform.openai.com | https://aistudio.google.com |
| **Config File** | .env.codex | .env.gemini |
| **Environment Var** | OPENAI_API_KEY | GEMINI_API_KEY |
| **Entry Point** | run-codex.ps1 | run-gemini.ps1 |

## 🚀 Usage

### Codex (OpenAI)

```powershell
cd script-codex
notepad .env.codex                # Add OpenAI API key
.\run-codex.ps1
.\run-codex.ps1 "analyze code"
.\run-codex.ps1 exec "refactor"
```

### Gemini (Google)

```powershell
cd script-gemini
notepad .env.gemini               # Add Google API key
.\run-gemini.ps1
.\run-gemini.ps1 "what is AI?"
.\run-gemini.ps1 "explain ML"
```

## 📋 Commands

### Codex

```
.\run-codex.ps1 help              Show help
.\run-codex.ps1                   Interactive
.\run-codex.ps1 "prompt"          With prompt
.\run-codex.ps1 exec "prompt"     Auto-execute
.\run-codex.ps1 check             Check setup
.\run-codex.ps1 setup             Setup
.\run-codex.ps1 login             Login
.\run-codex.ps1 device-login      Device auth
```

### Gemini

```
.\run-gemini.ps1 help             Show help
.\run-gemini.ps1                  Interactive
.\run-gemini.ps1 "prompt"         With prompt
.\run-gemini.ps1 check            Check setup
.\run-gemini.ps1 setup            Setup
```

## 🔐 Get API Keys

### Codex (OpenAI)

1. https://platform.openai.com/api-keys
2. Sign in
3. "Create new secret key"
4. Copy key (starts with `sk-`)
5. Paste into `script-codex/.env.codex`

### Gemini (Google)

1. https://aistudio.google.com/app/apikeys
2. Sign in with Google
3. "Create API Key"
4. Copy key (starts with `AIzaSy`)
5. Paste into `script-gemini/.env.gemini`

## ✨ Architecture (Identical)

Both use the same pattern:

```
run-<tool>.ps1 (dispatcher)
  ├─→ helper/check-env.ps1 (verify)
  ├─→ helper/setup-env.sh (WSL: install)
  └─→ helper/run-<tool>-impl.sh (launch)
```

This ensures:
- ✅ Automatic checks on startup
- ✅ Automatic setup if needed
- ✅ Clear error messages
- ✅ Consistent experience

## 🎯 Use Cases

### Codex (Code-focused)

- Code analysis
- Refactoring
- Bug fixing
- Documentation generation
- Test writing

### Gemini (General-purpose)

- Q&A
- Brainstorming
- Writing
- Research
- Learning

## 🚀 Quick Start (Both)

```powershell
# Codex
cd script-codex
notepad .env.codex
.\run-codex.ps1

# Gemini  
cd script-gemini
notepad .env.gemini
.\run-gemini.ps1
```

## 📝 Configuration Files

### script-codex/.env.codex

```
OPENAI_API_KEY=sk-...
```

### script-gemini/.env.gemini

```
GEMINI_API_KEY=AIzaSy...
```

## ✅ Status

Both systems are:
- ✅ Fully configured
- ✅ Automatically setting up
- ✅ Ready to use
- ✅ Portable (copy entire folders)
- ✅ Identical structure

## 🎓 Comparison Table

| Task | Codex | Gemini |
|------|-------|--------|
| Code analysis | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Refactoring | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Q&A | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Writing | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Learning | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Speed | Fast | Fast |
| Cost | Paid | Free tier available |

## 🚀 Ready!

Both tools are ready to use:

```powershell
# Codex
.\script-codex\run-codex.ps1

# Gemini
.\script-gemini\run-gemini.ps1
```

Choose the right tool for your task! 🎯

---

**Next Steps:**

1. Add API keys to both `.env` files
2. Run either tool
3. Start using them!

💡 Pro tip: Use both together for best results!
- Codex for code
- Gemini for ideas & research
