# 🚀 SIMPLE SETUP GUIDE - College Voice Agent

## ⚠️ Current Issues Detected:
1. **Docker is not running** (not required for local setup)
2. **PowerShell execution policy blocking npm**

## ✅ EASIEST SETUP (3 Steps):

### Step 1: Install Prerequisites

Download and install these if you haven't:

1. **Node.js** (v18+): https://nodejs.org/
   - Download the LTS version
   - Install with default settings
   
2. **Python** (v3.11+): https://www.python.org/downloads/
   - Check "Add Python to PATH" during installation
   
3. **OLLAMA**: https://ollama.ai/
   - Download and install
   - It will run automatically

### Step 2: Run Setup Script

**Double-click** this file in the project folder:
```
setup.bat
```

This will install all dependencies automatically.

### Step 3: Start OLLAMA and Pull Model

Open a new Command Prompt (not PowerShell) and run:

```cmd
ollama serve
```

In **another** Command Prompt, run:

```cmd
ollama pull llama3.2:3b
```

(This downloads ~2GB, takes 5-10 minutes)

### Step 4: Start the Application

**Double-click** this file:
```
start-app.bat
```

This will:
- Start the backend server (http://localhost:8000)
- Start the frontend server (http://localhost:5173)
- Open your browser automatically

---

## 🔧 Manual Setup (If Scripts Don't Work)

### Terminal 1 - Backend:
```cmd
cd c:\Users\ANAMIKA\OneDrive\Desktop\college\college-agent\backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Terminal 2 - Frontend:
```cmd
cd c:\Users\ANAMIKA\OneDrive\Desktop\college\college-agent\frontend
npm install
npm run dev
```

### Terminal 3 - OLLAMA:
```cmd
ollama serve
```

Then in another terminal:
```cmd
ollama pull llama3.2:3b
```

---

## 🌐 Access the Application

Once running:
- **Voice Chat**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5173/admin
- **API Docs**: http://localhost:8000/docs

---

## ❌ Troubleshooting

### "npm is not recognized"
- Reinstall Node.js from https://nodejs.org/
- Make sure to check "Add to PATH"
- Restart your computer

### "python is not recognized"
- Reinstall Python
- Check "Add Python to PATH" during installation
- Restart your computer

### "PowerShell execution policy error"
- Use Command Prompt (cmd) instead of PowerShell
- Or run: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### Port already in use
```cmd
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F

# Kill process on port 5173
netstat -ano | findstr :5173
taskkill /PID <PID_NUMBER> /F
```

### OLLAMA not connecting
- Make sure `ollama serve` is running in a terminal
- Check http://localhost:11434 in browser
- Restart OLLAMA

---

## 📝 Quick Test

1. Go to http://localhost:5173/admin
2. Upload a test PDF or Excel file
3. Go to http://localhost:5173
4. Click the microphone and speak OR type a question
5. Get instant answers!

---

## 💡 Tips

- **Use Command Prompt (cmd)** instead of PowerShell to avoid permission issues
- **Keep OLLAMA running** in a separate terminal
- **First time setup takes 10-15 minutes** (downloading model)
- **After setup, starting takes 30 seconds**

---

## 🆘 Still Not Working?

Let me know which step is failing and I'll help you fix it!
