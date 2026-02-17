import os
import json
import re
import base64
import requests
import io
import streamlit as st
from dotenv import load_dotenv
import groq
from datetime import datetime
import PyPDF2
from PIL import Image
from streamlit_mic_recorder import mic_recorder

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="AI Health Assistant",
    page_icon="🏥",
    layout="wide"
)

# Simple CSS for clean UI without fancy colors
st.markdown("""
<style>
    /* Keep text colors black and UI simple */
    body {
        color: black;
    }
    
    /* Make chat container more compact */
    .stChatMessageContent {
        padding: 5px 10px;
    }
    
    /* Remove unnecessary padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
    }
    
    /* Make buttons simple */
    .stButton button {
        border-radius: 4px;
    }
    
    /* Hide the default chat input */
    .stChatInput {
        display: none;
    }
    
    /* More compact layout */
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    /* File uploader styling */
    .stFileUploader {
        margin-bottom: 0.5rem;
    }
    
    /* Style for response option buttons */
    .stButton button:hover {
        background-color: #f0f0f0;
    }
    
    /* Style for diagnosis complete indicator */
    .diagnosis-complete {
        background-color: transparent;
        padding: 5px 0px;
        border-radius: 0px;
        border-left: 3px solid #4CAF50;
        padding-left: 10px;
        margin: 15px 0;
        font-weight: 600;
        color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize the Groq client for text processing
client = groq.Client(api_key=os.environ.get("GROQ_API_KEY"))

# Initialize the OpenAI client for vision capabilities (using their API)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Load symptoms map from your existing JSON file
@st.cache_data
def load_symptoms_map():
    try:
        with open('data/symptoms_map.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Symptoms map file not found. Please make sure data/symptoms_map.json exists.")
        return {}

# Improved system prompt with emphasis on proper diagnosis completion
SYSTEM_PROMPT = """You are an AI-powered health assistant specializing in concise symptom analysis and targeted diagnostic information.

CORE PRINCIPLES:
1. EXTREME BREVITY - Responses must be compact, direct, and to the point
2. PRECISION - Focus only on the most likely conditions based on symptoms
3. STRUCTURED ANALYSIS - Use bullet points and minimal paragraphs
4. DATA-DRIVEN - Base assessments on specific symptoms reported, not generalities
5. NO FILLER TEXT - Eliminate pleasantries, redundancies, and general health advice

RESPONSE LENGTH GUIDANCE:
- Questions: 1-2 direct questions with no preamble
- Analyses: 2-3 short sentences per condition
- Next steps: Bullet points only, 1 sentence each
- Total response: Aim for 100-150 words maximum

DIAGNOSTIC APPROACH:
1. ASK ONLY ESSENTIAL QUESTIONS - Focus on the specific information needed
2. IDENTIFY PATTERNS - Connect symptoms to likely conditions without lengthy explanation
3. PRIORITIZE CLARITY - Present conclusions in simple, direct language
4. AVOID HEDGING - Be direct about what's most likely while maintaining accuracy

NEXT STEPS & RELIEF MEDICINE RULES:
1. ALWAYS suggest specific categories of medicine for symptom relief (e.g., Antacids for acidity, Paracetamol for pain, Antihistamines for allergies).
2. Present these as the first bullet point(s) in the "Next steps" section.
3. Word it as "Consider taking [medicine category/type] for temporary relief" or "Over-the-counter [medicine] may help with [symptom]".
4. Maintain the disclaimer: "Consult a pharmacist or doctor before taking any medication."

RESPONSE STRUCTURE:
1. One-sentence acknowledgment (optional)
2. If needed: 1-2 specific, direct questions
3. For diagnosis: 
   - Most likely explanation in 1-2 sentences
   - Key differentiating factors (if relevant) in 1 sentence
   - Next steps as brief bullet points (MUST include relief medicine suggestions)

Always provide the following medical disclaimer at the end in italics:
*Disclaimer: This assessment is not a definitive diagnosis. Consult a qualified healthcare professional for accurate diagnosis and treatment.*

Be precise, direct, and concise.

MULTI-LANGUAGE & REGIONAL SUPPORT:
- INPUT: Support interactions in Hindi, Hinglish, and other Indian regional languages.
- OUTPUT: ALWAYS RESPOND IN ENGLISH. NEVER RESPOND IN HINDI OR ANY OTHER LANGUAGE. 
- Even if the user asks a question in Hindi, your response MUST be in clear, concise English.
- Use professional medical terminology in English.

DIAGNOSIS COMPLETION RULES:
- ONLY use "DIAGNOSIS COMPLETE: [specific condition]" when you have enough information to make a definitive diagnosis
- NEVER include "DIAGNOSIS COMPLETE" if you are still asking diagnostic questions
- NEVER use "DIAGNOSIS COMPLETE: Not possible without further information" - this is contradictory
- If you need more information, simply ask questions without marking diagnosis as complete
- A complete diagnosis means you've identified a specific condition with reasonable confidence
"""

# Enhanced prompt for generating quick response options for users
RESPONSE_OPTIONS_PROMPT = """Based on the user's message: "{user_message}"
And your response: "{assistant_response}"

Generate 4 brief responses the user might want to send next. 
RULES:
1. OUTPUT MUST BE IN ENGLISH ONLY.
2. Each should be under 60 characters.
3. Conversational and direct.
4. Provide new medical information or answer questions.

FORMAT:
Response Options:
- [Symptom detail]
- [Medical history]
- [Lifestyle factor]
- [Direct answer]
"""

# Safety check for emergency symptoms
def check_for_emergency_symptoms(message):
    emergency_symptoms = [
        "difficulty breathing", "severe chest pain", "severe bleeding",
        "loss of consciousness", "seizure", "stroke", "heart attack",
        "suicidal", "suicide", "kill myself", "end my life"
    ]
    
    message = message.lower()
    for symptom in emergency_symptoms:
        if symptom in message:
            return True, symptom
    
    return False, ""

# Greatly improved function to check if diagnosis is complete
# Replace the is_diagnosis_complete function with this more accurate version
def is_diagnosis_complete(assistant_response):
    # First, check for questions - if there are questions, diagnosis is not complete
    question_indicators = [
        r'\?',  # Question mark
        r'(how|what|when|where|why|do|does|have|has|can|could) you',
        r'(tell|share|describe|provide) (me|us|more)',
        r'(need|would like|want) (to know|more information)',
        r'let me know'
    ]
    
    has_questions = False
    for pattern in question_indicators:
        if re.search(pattern, assistant_response, re.IGNORECASE):
            has_questions = True
            break
    
    if has_questions:
        return False  # If there are questions, diagnosis is not complete
    
    # Check for specific diagnosis patterns
    
    # Check for section headers with "condition" or "diagnosis"
    condition_headers = [
        r'(likely|possible|probable|diagnosed|confirmed|primary) (condition|diagnosis)[\s:]',
        r'(assessment|diagnosis|impression)[\s:]',
        r'(diagnosed|confirmed) with'
    ]
    
    has_condition_header = False
    for pattern in condition_headers:
        if re.search(pattern, assistant_response, re.IGNORECASE):
            has_condition_header = True
            break
            
    # Check for specific conditions mentioned
    condition_indicators = [
        r'shingles',
        r'herpes zoster',
        r'dermatitis',
        r'(infection|disorder|disease|syndrome)',
        r'(likely|probable) ([a-zA-Z\s]+)',
    ]
    
    has_condition = False
    for pattern in condition_indicators:
        if re.search(pattern, assistant_response, re.IGNORECASE):
            has_condition = True
            break
    
    # Check for next steps/treatment recommendations
    next_steps_indicators = [
        r'next steps[\s:]',
        r'(recommend|suggested) (treatment|steps|approach)',
        r'steps you should take',
        r'you should (see|consult)',
        r'treatment (options|plan)',
        r'see a doctor',
        r'(physical examination|medical history)'
    ]
    
    has_next_steps = False
    for pattern in next_steps_indicators:
        if re.search(pattern, assistant_response, re.IGNORECASE):
            has_next_steps = True
            break
    
    # If there's a condition header or specific condition mentioned, AND next steps,
    # and NO questions, consider the diagnosis complete
    if (has_condition_header or has_condition) and has_next_steps and not has_questions:
        return True
        
    # Special pattern match for the exact format shown in the example
    exact_pattern = r'(likely|possible) condition:\s*\n\s*([a-zA-Z\s\(\)]+)'
    if re.search(exact_pattern, assistant_response, re.IGNORECASE) and has_next_steps:
        return True
    
    # Also check for the DIAGNOSIS COMPLETE marker as a backup
    if re.search(r'DIAGNOSIS COMPLETE:\s*([a-zA-Z\s]+)', assistant_response, re.IGNORECASE):
        diagnosis = re.search(r'DIAGNOSIS COMPLETE:\s*([a-zA-Z\s]+)', assistant_response, re.IGNORECASE).group(1).strip().lower()
        # Check if it's a real diagnosis and not "not possible" or similar
        if "not" not in diagnosis and "unclear" not in diagnosis and "impossible" not in diagnosis:
            return True
    
    return False

# Check if there are previous messages with a complete diagnosis
def is_diagnosis_already_complete(chat_history):
    # Look through message history for valid diagnosis completion markers
    for message in chat_history:
        if message["role"] == "assistant":
            if isinstance(message["content"], str):
                # Use the improved diagnosis detection function
                if is_diagnosis_complete(message["content"]):
                    return True
            # Also check the stored diagnosis_complete flag
            if isinstance(message.get("diagnosis_complete"), bool) and message["diagnosis_complete"]:
                return True
    return False

# Generate improved quick response options for the user to select
def generate_quick_response_options(user_message, assistant_response, chat_history):
    # Skip generating options if diagnosis is complete (using the improved check)
    if is_diagnosis_complete(assistant_response) or is_diagnosis_already_complete(chat_history):
        return []  # Return empty list to prevent any response options
        
    prompt = RESPONSE_OPTIONS_PROMPT.format(
        user_message=user_message,
        assistant_response=assistant_response
    )
    
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": "You create brief, helpful response options for medical conversations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,  # Slightly higher temperature for more creative responses
        max_tokens=300
    )
    
    result = response.choices[0].message.content
    
    # Extract the response options
    options = []
    
    # First look for bullet points after "Response Options:" section
    match = re.search(r'Response Options:(.*?)(?=$)', result, re.DOTALL)
    if match:
        section = match.group(1).strip()
        options = re.findall(r'[-•*]\s*(.*?)(?=\n[-•*]|\n\n|$)', section, re.DOTALL)
        options = [o.strip() for o in options if o.strip()]
    
    if not options:
        options = re.findall(r'[-•*]\s*(.*?)(?=\n[-•*]|\n\n|$)', result, re.DOTALL)
        options = [o.strip() for o in options if o.strip()]
    
    if not options:
        options = re.findall(r'\d+\.\s+(.*?)(?=\n\d+\.|\n\n|$)', result, re.DOTALL)
        options = [o.strip() for o in options if o.strip()]
    
    # If we still don't have 4 options, create default ones
    while len(options) < 4:
        options.append(f"I need more information about that.")
    
    return options[:4]

def find_matching_conditions(message, symptoms_map):
    message_lower = message.lower()
    matches = {}
    
    # Pre-tokenize message for faster symptom lookup pre-filtering
    message_words = set(re.findall(r'\b\w+\b', message_lower))
    
    for symptom, conditions in symptoms_map.items():
        symptom_lower = symptom.lower()
        
        # Optimization: Fast pre-filtering
        # If none of the words in the symptom phrase are even in the message words, skip heavy string matching
        symptom_words = re.findall(r'\b\w+\b', symptom_lower)
        if symptom_words and not any(word in message_words for word in symptom_words):
            continue
            
        if symptom_lower in message_lower:
            for condition_info in conditions:
                condition = condition_info["condition"]
                if condition not in matches:
                    matches[condition] = {
                        "score": 1,
                        "symptoms": {symptom},  # Use set for uniqueness and efficiency
                        "severity": condition_info.get("severity", "medium")
                    }
                else:
                    if symptom not in matches[condition]["symptoms"]:
                        matches[condition]["score"] += 1
                        matches[condition]["symptoms"].add(symptom)
    
    result = []
    for condition, info in matches.items():
        result.append({
            "condition": condition,
            "score": info["score"],
            "symptoms": list(info["symptoms"]),
            "severity": info["severity"]
        })
    
    result.sort(key=lambda x: x["score"], reverse=True)
    return result[:7]  # Return top 7 matches for broader analysis

# Enhanced conversation stage analysis
def analyze_conversation_stage(chat_history):
    # First check if diagnosis has already been completed in previous messages
    for msg in reversed(chat_history):
        if msg["role"] == "assistant":
            if isinstance(msg["content"], str) and is_diagnosis_complete(msg["content"]):
                return "diagnosis_complete"
            if "diagnosis_complete" in msg and msg["diagnosis_complete"]:
                return "diagnosis_complete"
    
    if len(chat_history) < 4:
        return "initial_gathering"
    
    # Count user messages that contain symptom information
    symptom_keywords = ["pain", "ache", "feel", "hurt", "symptom", "experiencing", 
                       "discomfort", "fever", "cough", "headache", "nausea", 
                       "vomiting", "dizzy", "rash", "swelling", "fatigue"]
    
    symptom_messages = 0
    symptom_details = 0
    
    # Look for specific symptom details
    detail_indicators = ["for", "since", "days", "weeks", "started", "began", 
                         "worse", "better", "when", "after", "during", "before",
                         "morning", "night", "severity", "intense", "mild", 
                         "medication", "treatment"]
    
    for msg in chat_history:
        if msg["role"] == "user":
            content = msg["content"]
            if isinstance(content, dict) and "text" in content:
                content = content["text"]
            elif not isinstance(content, str):
                continue
                
            content = content.lower()
            if any(keyword in content for keyword in symptom_keywords):
                symptom_messages += 1
            
            if any(indicator in content for indicator in detail_indicators):
                symptom_details += 1
    
    if symptom_messages >= 3 or (symptom_messages >= 2 and symptom_details >= 2):
        return "enough_information"
    elif symptom_messages >= 1:
        return "needs_more_information"
    else:
        return "initial_gathering"

# Function to analyze image with GPT-4 Vision
def analyze_image_with_vision(image_file, prompt_text):
    try:
        # Convert the image to base64
        image_file.seek(0)
        image_bytes = image_file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        # Create the payload with the image and prompt
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyze this medical image in detail. {prompt_text} Focus specifically on identifying any visible medical conditions, abnormalities, or symptoms. Provide a detailed medical assessment of what you see."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500
        }
        
        # Make the API call
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response_data = response.json()
        
        # Extract the image analysis
        if 'choices' in response_data and len(response_data['choices']) > 0:
            image_analysis = response_data['choices'][0]['message']['content']
            return image_analysis
        else:
            return "Error: Could not analyze the image. API response did not contain expected data."
    
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

# Function to analyze image using Groq with llava model (alternative)
def analyze_image_with_llava(image_file, prompt_text):
    try:
        # Convert the image to base64
        image_file.seek(0)
        image_bytes = image_file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create the prompt for the model
        prompt = f"""
        USER: <image>
        Analyze this medical image in detail. {prompt_text} Focus specifically on identifying any visible medical conditions, abnormalities, or symptoms. Provide a detailed medical assessment of what you see.
        
        ASSISTANT:
        """
        
        # Call Groq API with llava model
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error analyzing image with Llava: {str(e)}"

# Function to transcribe audio using Groq Whisper
def transcribe_audio_with_whisper(audio_bytes):
    try:
        # Save audio bytes to a temporary file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.wav"
        
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            response_format="text",
            language="hi"  # Hinting at Hindi/Hinglish though Whisper is auto-detecting
        )
        return transcription
    except Exception as e:
        return f"Error transcribing audio: {str(e)}"

# Function to determine file type and process accordingly
def process_file(uploaded_file, user_message):
    if uploaded_file is None:
        return None, None
        
    file_type = uploaded_file.type
    file_name = uploaded_file.name
    
    # Process image files with visual understanding
    if file_type.startswith('image/'):
        try:
            # Use Vision API to analyze the image content
            uploaded_file.seek(0)  # Reset file pointer
            
            # Try using GPT-4 Vision first
            if OPENAI_API_KEY:
                image_analysis = analyze_image_with_vision(uploaded_file, user_message)
            # Fall back to LLaVA if no OpenAI key
            else:
                image_analysis = analyze_image_with_llava(uploaded_file, user_message)
                
            return "image", {
                "file_name": file_name,
                "file_obj": uploaded_file,
                "analysis": image_analysis
            }
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
            return None, None
    
    # Process PDF files
    elif file_type == 'application/pdf':
        try:
            # Extract text from PDF
            uploaded_file.seek(0)  # Reset file pointer
            pdf_text = extract_text_from_pdf(uploaded_file)
            return "pdf", {
                "file_name": file_name,
                "file_obj": uploaded_file,
                "text": pdf_text
            }
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return None, None
    
    else:
        st.warning(f"Unsupported file type: {file_type}")
        return None, None

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            pdf_text += page.extract_text() + "\n\n"
        return pdf_text.strip()
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

# Process user message and generate response
def process_message(message, files, chat_history, symptoms_map):
    # First check if diagnosis has already been completed in previous messages
    diagnosis_already_completed = is_diagnosis_already_complete(chat_history)
    
    multimodal_content = {}
    combined_text = message
    
    # Process any uploaded files
    if files:
        file_descriptions = []
        
        for file_data in files:
            file_type, file_info = file_data
            
            if file_type == "image":
                # Use the detailed image analysis instead of just OCR text
                image_analysis = file_info["analysis"]
                multimodal_content["image_analysis"] = image_analysis
                file_descriptions.append(f"IMAGE ANALYSIS: {image_analysis}")
                
            elif file_type == "pdf":
                pdf_text = file_info["text"]
                multimodal_content["pdf_text"] = pdf_text
                pdf_summary = f"DOCUMENT CONTENT: {pdf_text[:500]}"
                if len(pdf_text) > 500:
                    pdf_summary += "... [document truncated]"
                file_descriptions.append(pdf_summary)
        
        # Add file content to the message
        if file_descriptions:
            combined_text += "\n\n" + "\n\n".join(file_descriptions)
    
    # Check for emergency symptoms
    is_emergency, emergency_symptom = check_for_emergency_symptoms(combined_text)
    
    # Find matching conditions from symptoms map
    matches = find_matching_conditions(combined_text, symptoms_map)
    
    # Analyze conversation stage
    conversation_stage = analyze_conversation_stage(chat_history)
    
    # Build context for the AI with more precise guidance
    conditions_context = ""
    if matches:
        conditions_context = "Potential conditions based on symptom matching (focus on top 3 most likely):\n"
        for i, match in enumerate(matches[:3], 1):  # Only show top 3 matches for focus
            conditions_context += f"{i}. {match['condition']} (matching symptoms: {', '.join(match['symptoms'][:3])}"
            if len(match['symptoms']) > 3:
                conditions_context += f" and {len(match['symptoms']) - 3} more"
            conditions_context += f") - {match['severity']} severity\n"
    
    # Add guidance based on conversation stage with more precise instructions
    stage_guidance = ""
    if diagnosis_already_completed or conversation_stage == "diagnosis_complete":
        stage_guidance = "\nCONVERSATION STAGE: DIAGNOSIS COMPLETE. Keep responses brief. Focus only on answering specific questions about the diagnosis, management, or treatment."
    elif conversation_stage == "initial_gathering":
        stage_guidance = "\nCONVERSATION STAGE: INITIAL INFORMATION GATHERING. Ask 1-2 direct questions about symptoms. Be extremely concise."
    elif conversation_stage == "needs_more_information":
        stage_guidance = "\nCONVERSATION STAGE: NEED MORE DETAILS. Ask 1-2 specific follow-up questions. Focus only on what's needed to narrow down possibilities."
    else:
        stage_guidance = "\nCONVERSATION STAGE: SUFFICIENT INFORMATION. Provide a focused analysis of only the most likely cause. Keep explanations under 3 sentences total."
    
    # Add brevity guidance
    brevity_guidance = "\nBREVITY REQUIREMENTS: Keep your entire response under 150 words. Use bullet points when possible. Eliminate all unnecessary words and phrases. Be direct and to the point."
    
    # Add multimodal context if any
    multimodal_guidance = ""
    if multimodal_content:
        if "image_analysis" in multimodal_content:
            multimodal_guidance = "\nMULTIMODAL CONTENT: The user has shared a medical image. Use the detailed image analysis to inform your diagnostic assessment. Incorporate visual findings with any textual symptoms."
        else:
            multimodal_guidance = "\nMULTIMODAL CONTENT: The user has shared files. Integrate this extracted text information with their message for a comprehensive analysis."
    
    # Prepare the complete prompt with context
    ai_messages = [
        {"role": "system", "content": SYSTEM_PROMPT + stage_guidance + brevity_guidance + multimodal_guidance}
    ]
    
    # Add chat history
    for msg in chat_history:
        # Handle different message formats in history
        if isinstance(msg["content"], dict):
            text_content = msg["content"].get("text", "")
            ai_messages.append({"role": msg["role"], "content": text_content})
        else:
            ai_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add the current message with context
    prompt = combined_text
    if conditions_context:
        prompt += f"\n\nREFERENCE INFORMATION (NOT VISIBLE TO USER):\n{conditions_context}"
    
    # Add emergency warning if needed
    if is_emergency:
        prompt += f"\n\nIMPORTANT: The user mentioned '{emergency_symptom}' which may indicate an emergency situation. Prioritize advising them to seek immediate medical attention."
    
    # Add specific guidance on diagnosis completion markers
    prompt += "\n\nIMPORTANT: Only use 'DIAGNOSIS COMPLETE: [specific condition]' if you've reached a definitive diagnosis. NEVER use this marker if you're still asking questions. NEVER use 'DIAGNOSIS COMPLETE: Not possible without further information' as this is contradictory."
    
    # If in final diagnosis stage or enough info, suggest adding the completion marker
    if conversation_stage == "enough_information" and not diagnosis_already_completed:
        prompt += "\n\nIf you have sufficient information for a definitive diagnosis, include 'DIAGNOSIS COMPLETE: [condition name]' at the end of your message before the disclaimer."
    
    # If diagnosis already complete, remind the AI not to ask diagnostic questions
    if diagnosis_already_completed:
        prompt += "\n\nIMPORTANT: A diagnosis has already been made in this conversation. Do not ask any new diagnostic questions. Focus only on answering the user's current question about management or treatment."
    
    # Add specific instruction to be concise
    prompt += "\n\nIMPORTANT: Keep your response extremely concise and to the point. Aim for 100-150 words maximum."
    
    # Add a final reminder about the language rule to ensure enforcement
    ai_messages.append({"role": "system", "content": "FINAL REMINDER: YOUR RESPONSE MUST BE IN ENGLISH ONLY. DO NOT USE HINDI OR HINGLISH IN YOUR OUTPUT."})
    
    ai_messages.append({"role": "user", "content": prompt})
    
    # Get response from the AI using Llama-4 Scout with settings for precision and brevity
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=ai_messages,
        temperature=0.1,    # Lower temperature for more focused responses
        max_tokens=500,     # Reduce max tokens to encourage brevity
        top_p=0.5           # Lower top_p for more focused and concise responses
    )
    
    ai_response = response.choices[0].message.content
    
    # Add emergency warning to the displayed response if needed
    if is_emergency:
        ai_response = "⚠️ **EMERGENCY WARNING**: This sounds like a potentially serious medical situation that may require immediate attention. Please contact emergency services or go to the nearest emergency room.\n\n" + ai_response
    
    # Add abbreviated medical disclaimer if not already present
    if "not a substitute for professional medical advice" not in ai_response.lower():
        ai_response += "\n\n*Not a substitute for professional medical advice. Consult a healthcare provider.*"
    
    # Check if this response completes the diagnosis or if it was already complete
    # Use the improved detection that checks for questions
    diagnosis_completed = is_diagnosis_complete(ai_response) or diagnosis_already_completed
    
    # Generate quick response options only if diagnosis is not complete
    quick_responses = []
    if not diagnosis_completed:
        quick_responses = generate_quick_response_options(message, ai_response, chat_history)
    
    # Fix for the specific bug: Remove diagnosis marker if asking questions
    if "DIAGNOSIS COMPLETE:" in ai_response and re.search(r'\?', ai_response):
        # Remove the diagnosis complete marker since we're still asking questions
        ai_response = re.sub(r'DIAGNOSIS COMPLETE:.*?(\n|$)', '', ai_response)
        diagnosis_completed = False  # Override the diagnosis completed flag
    
    return ai_response, quick_responses, matches, diagnosis_completed

# Helper function to set session state key-value
def set_suggestion(suggestion):
    st.session_state.user_input = suggestion

# Function to get current date and time formatted
def get_current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Main application
def main():
    # Check for vision API key
    if not OPENAI_API_KEY and not client.api_key:
        st.error("Warning: No API key found for image analysis. Please set OPENAI_API_KEY or ensure Groq supports multimodal capabilities.")
    
    # Load symptoms map
    symptoms_map = load_symptoms_map()
    if not symptoms_map:
        st.error("No symptoms data found. Please check your symptoms_map.json file.")
        return
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Initialize user input state if not exists
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

    # Professional Header CSS
    st.markdown("""
    <style>
        .prof-header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
            margin-bottom: 20px;
        }
        .prof-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(90deg, #1e3799, #00d2d3);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
        }
        .session-info {
            font-size: 0.8rem;
            color: #7f8c8d;
            text-align: right;
        }
        .medical-disclosure {
            background-color: #f8f9fa;
            border-left: 4px solid #34495e;
            padding: 12px 20px;
            font-size: 0.85rem;
            color: #576574;
            border-radius: 4px;
            margin-bottom: 25px;
            line-height: 1.4;
        }
        .medical-disclosure b {
            color: #2c3e50;
        }
    </style>
    """, unsafe_allow_html=True)

    # Professional Header
    st.markdown(f"""
    <div class="prof-header-container">
        <div class="prof-title">AI HEALTH ASSISTANT</div>
        <div class="session-info">
            ID: Khush2509<br>
            Session: {get_current_datetime()}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Medical Disclosure Section
    st.markdown("""
    <div class="medical-disclosure">
        <b>Medical Disclosure:</b> This platform uses artificial intelligence to provide educational health information. 
        It is <b>not</b> a substitute for professional medical advice, diagnosis, or treatment. 
        If you are experiencing a medical emergency, please contact local emergency services immediately.
    </div>
    """, unsafe_allow_html=True)

    # Reset button in a clean column
    col_empty, col_reset = st.columns([5, 1])
    with col_reset:
        if st.button("Reset Session", use_container_width=True):
            st.session_state.messages = []
            st.session_state.user_input = ""
            st.rerun()
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for idx, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                # Handle different types of content
                if isinstance(message["content"], dict):
                    # Display text
                    if "text" in message["content"]:
                        st.markdown(message["content"]["text"])
                    
                    # Display files if present
                    if "files" in message["content"]:
                        for file_type, file_info in message["content"]["files"]:
                            if file_type == "image":
                                st.image(file_info["file_obj"], caption=f"Uploaded image: {file_info['file_name']}")
                            elif file_type == "pdf":
                                st.info(f"PDF uploaded: {file_info['file_name']}")
                else:
                    st.markdown(message["content"])
                
                # Display diagnosis complete indicator if applicable
                if message["role"] == "assistant" and "diagnosis_complete" in message and message["diagnosis_complete"]:
                    st.markdown("<div class='diagnosis-complete'>✅ Diagnosis complete</div>", unsafe_allow_html=True)
                
                # Display quick response options after assistant messages
                if message["role"] == "assistant" and idx == len(st.session_state.messages) - 1:
                    if "quick_responses" in message and message["quick_responses"] and len(message["quick_responses"]) > 0:
                        st.markdown("---")
                        st.caption("**Instant Reply (Click to send):**")
                        
                        # Use columns for a more compact layout
                        cols = st.columns(min(len(message["quick_responses"]), 2))
                        for i in range(0, len(message["quick_responses"]), 2):
                            for j, col in enumerate(cols):
                                if i+j < len(message["quick_responses"]):
                                    response = message["quick_responses"][i+j]
                                    # Use a button that auto-submits the suggestion
                                    if col.button(f"{response}", key=f"response_{idx}_{i+j}", use_container_width=True):
                                        st.session_state.suggestion_submitted = response
                                        st.rerun()
    
    # Create multimodal input form
    with st.form(key="multimodal_form", clear_on_submit=True):
        # Text input
        user_message = st.text_input(
            "Type your message:",
            value=st.session_state.user_input,
            key="message_input",
            label_visibility="visible"
        )
        
        # Combined file upload section
        st.caption("Attach files (optional):")
        uploaded_files = st.file_uploader(
            "Upload images or medical documents", 
            type=["png", "jpg", "jpeg", "pdf"],
            key="file_uploader",
            accept_multiple_files=True,
            help="Upload images showing symptoms or medical records (PDF)"
        )
        
        # Voice recorder
        st.caption("Or record your symptoms:")
        audio_data = mic_recorder(
            start_prompt="🎤 Start Recording",
            stop_prompt="🛑 Stop Recording",
            key="mic_recorder",
            just_once=True
        )
        
        # Submit button
        submit_button = st.form_submit_button("Send", type="primary")
    
    # Process form submission
    suggestion_submitted = st.session_state.get("suggestion_submitted", None)
    
    if (submit_button or audio_data or suggestion_submitted) and (user_message or uploaded_files or audio_data or suggestion_submitted):
        # Store the message temporarily
        if suggestion_submitted:
            temp_message = suggestion_submitted
            # Clear the suggestion from session state immediately
            st.session_state.suggestion_submitted = None
        else:
            temp_message = user_message
        
        # If voice data exists, transcribe it
        if audio_data and audio_data.get("bytes"):
            with st.spinner("Transcribing your voice..."):
                transcribed_text = transcribe_audio_with_whisper(audio_data["bytes"])
                if not transcribed_text.startswith("Error"):
                    if temp_message:
                        temp_message += "\n\n(Voice Input): " + transcribed_text
                    else:
                        temp_message = transcribed_text
                else:
                    st.error(transcribed_text)
        
        # Process uploaded files
        processed_files = []
        if uploaded_files:
            for file in uploaded_files:
                file_type, file_info = process_file(file, temp_message)
                if file_type and file_info:
                    processed_files.append((file_type, file_info))
        
        # Clear the input from session state
        st.session_state.user_input = ""
        
        # Create a structured message content
        if processed_files:
            message_content = {
                "text": temp_message,
                "files": processed_files
            }
            st.session_state.messages.append({"role": "user", "content": message_content})
        else:
            st.session_state.messages.append({"role": "user", "content": temp_message})
        
        # Display user message with any uploads
        with st.chat_message("user"):
            st.markdown(temp_message)
            
            # Display uploaded files
            for file_type, file_info in processed_files:
                if file_type == "image":
                    st.image(file_info["file_obj"], caption=f"Uploaded image: {file_info['file_name']}", width=300)
                elif file_type == "pdf":
                    st.info(f"PDF uploaded: {file_info['file_name']}")
        
        # Process with health assistant
        with st.chat_message("assistant"):
            with st.spinner("Analyzing input..."):
                assistant_response, quick_responses, matches, diagnosis_completed = process_message(
                    temp_message, processed_files, st.session_state.messages, symptoms_map
                )
                st.markdown(assistant_response)
                
                # Show diagnosis complete indicator if applicable
                if diagnosis_completed:
                    st.markdown("<div class='diagnosis-complete'>✅ Diagnosis complete</div>", unsafe_allow_html=True)
        
        # Add assistant response to chat history
        st.session_state.messages.append({
            "role": "assistant", 
            "content": assistant_response,
            "quick_responses": quick_responses,
            "diagnosis_complete": diagnosis_completed
        })
        
        # Rerun to update the UI with quick responses
        st.rerun()

if __name__ == "__main__":
    main()

