# 🏥 AI Health Assistant

A modern, professional AI-powered health assistant built with **Streamlit** and **Groq Cloud**. It provides concise symptom analysis, medical report explanation, and temporary relief suggestions.

## ✨ Features
- **Symptom Analysis**: Quick and structured analysis of health concerns.
- **Multimodal Support**: Upload images or PDFs (medical reports) for AI analysis.
- **Voice Input**: Record your symptoms using the integrated voice-to-text feature.
- **Relief Suggestions**: Categorized over-the-counter medicine suggestions for temporary relief.
- **Professional UI**: Clean, clinical dashboard design with a "Khush2509" personalized ID.
- **Multi-language Input**: Supports Hindi/Hinglish input but always responds in professional English.

## 🛠️ Tech Stack
- **Frontend**: Streamlit
- **AI Models**: Groq (Llama 3 / Whisper) & OpenAI Vision
- **Environment**: Python 3.x

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+
- Groq API Key
- OpenAI API Key (Optional for Vision)

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd ai-health-chatbot-main

# Install dependencies
pip install -r req.txt
```

### 3. Setup Environment
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
```

### 4. Run the App
```bash
streamlit run app.py
```

## ⚖️ Disclaimer
*This assessment is not a definitive diagnosis. Consult a qualified healthcare professional for accurate diagnosis and treatment.*