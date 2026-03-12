# 🏥 AI Health Assistant

[![Groq Cloud](https://img.shields.io/badge/Powered%20by-Groq-orange)](https://groq.com/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A sophisticated, professional **Hybrid LLM-RAG Health Assistant**. Built with **Streamlit** and leveraging the speed of **Groq Cloud**, this assistant provides rapid symptom analysis, medical report interpretation, and actionable temporary relief suggestions by retrieving clinical data from a structured knowledge base.

## 🌟 Key Features

### 🔍 Intelligent RAG Symptom Analysis
- **Retrieval-Augmented Generation**: Combines the power of Large Language Models with a curated, structured knowledge base (`symptoms_map.json`) for grounded health assessments.
- **Dynamic Questioning**: Adaptive conversation flow that asks specific, diagnostic questions.
- **Brevity & Precision**: Responses are engineered for clinical clarity and extreme conciseness.
- **Multilingual Input**: Supports Hindi and Hinglish inputs while maintaining professional English outputs.

### 📄 Document & Image Intelligence
- **Medical Report Analysis**: Upload PDF reports (blood tests, prescriptions) for instant AI summarization and explanation.
- **Visual Assessment**: Integrated vision capabilities to analyze medical images and skin conditions.

### 🎙️ Voice-Activated Hygiene
- **Hands-Free Input**: Record symptoms via integrated voice-to-text using Groq's Whisper-large-v3 model.

### 💊 Actionable Next Steps
- **Relief Suggestions**: Specific categories of OTC medicine suggestions for temporary symptom relief.
- **Emergency Awareness**: Real-time detection of high-risk symptoms with immediate emergency redirection.

---

## 🛠️ Modern Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) - Premium, clinical dashboard aesthetic with custom CSS.
- **LLM Engine**: [Groq Cloud](https://groq.com/) (Llama-4 Scout / Whisper) for ultra-low latency processing.
- **Computer Vision**: OpenAI Vision / Llava for sophisticated image analysis.
- **Data Stores**: Structured JSON knowledge base for fast, deterministic symptom mapping.

---

## 🚀 Getting Started

### 📋 Prerequisites
- Python 3.8 or higher
- [Groq API Key](https://console.groq.com/)
- [OpenAI API Key](https://platform.openai.com/) (Optional, for advanced vision features)

### ⚙️ Installation

1. **Clone the Project**
   ```bash
   git clone https://github.com/khushshah103/AI-Health-Assistant.git
   cd AI-Health-Assistant
   ```

2. **Environment Setup**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### 🏃 Running the Application
```bash
streamlit run app.py
```

---

## 📁 Project Structure

```text
AI-Health-Assistant/
├── app.py                # Main Streamlit application and UI logic
├── data/
│   └── symptoms_map.json # Structured medical knowledge base
├── .env                  # Environment configurations (API Keys)
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation
```

---

The assistant follows a **Hybrid Retrieval-Augmented Generation (RAG) Pipeline**:
1. **Input Pre-processing**: Handles text, audio (Whisper), or visual (Vision) input.
2. **Deterministic Retrieval**: Matches user input against a structured `symptoms_map.json` using custom Python logic and pre-filtering optimizations.
3. **Augmented Reasoning**: The retrieved clinical context is injected into the LLM prompt (Llama-4 Scout via Groq) to ensure precise, grounded analysis.
4. **Safety Filter**: Proactively checks for emergency markers and applies mandatory medical disclaimers.

---

## ⚖️ Medical Disclaimer

> [!IMPORTANT]
> **This application is for informational purposes only.**
> It is NOT a medical device and does NOT provide definitive diagnoses or medical treatments. 
> Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition. Never disregard professional medical advice or delay in seeking it because of something you have read here.

---

## 👤 Author

Developed with ❤️ by **Khush Shah**  
GitHub: [@khushshah103](https://github.com/khushshah103)

---
*Powered by AI, designed for Health.*
