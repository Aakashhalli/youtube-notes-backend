from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
from fpdf import FPDF
import google.generativeai as genai
import os
import re

# Load environment variables (e.g., GOOGLE_API_KEY)
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize FastAPI app
app = FastAPI()

# CORS Middleware (adjust for your frontend URL if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081"],  # Replace * with frontend domain for production
    allow_credentials=True,
    allow_methods=["http://localhost:8081"],
    allow_headers=["http://localhost:8081"],
)

# Request model
class VideoRequest(BaseModel):
    youtube_url: str
    subject: str

# Helper: Clean up AI-generated text
def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

# Extract transcript from YouTube video
def extract_transcript(youtube_url: str):
    try:
        video_id = youtube_url.split("v=")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return transcript_text
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"

# Generate structured notes using Gemini
def generate_notes(transcript_text: str, subject: str):
    prompt = f"""
    Title: Structured Study Notes on {subject}

    As an AI assistant, your task is to generate **structured and detailed notes** from the transcript of a YouTube video. 

    The notes should be **well-formatted** and include:
    - **Main topics & key concepts** (as section headings).
    - **Bullet points or numbered lists** for explanations.
    - **Examples, formulas, or real-world applications** (if mentioned).
    - **Concise explanations** that improve readability.

    Transcript:
    {transcript_text}
    """
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return clean_text(response.text)

# Generate aptitude questions
def generate_aptitude_questions(subject: str):
    prompt = f"""
    Title: Placement Aptitude Questions for {subject}

    Generate 5-7 technical aptitude questions related to {subject}. Include:
    - Conceptual understanding
    - Problem-solving
    - Real-world applications
    - MCQs or open-ended questions

    Format the questions clearly with numbering.
    """
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return clean_text(response.text)

# Save notes + questions as PDF
def save_as_pdf(notes, questions, subject):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, f"Study Notes on {subject}", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Detailed Notes", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)

    for line in notes.split("\n"):
        if line.strip():
            if line.startswith(("-", "*", "•")):
                pdf.cell(10)
            pdf.multi_cell(0, 7, line)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Placement Aptitude Questions", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)

    for line in questions.split("\n"):
        if line.strip():
            if re.match(r"^\d+\.", line):
                pdf.ln(3)
            pdf.multi_cell(0, 7, line)

    filename = f"{subject.replace(' ', '_')}_notes.pdf"
    pdf.output(filename)
    return filename

# Health check
@app.get("/ping")
def ping():
    return {"message": "Server is running!"}

# Main route for processing
@app.post("/generate_notes")
def process_video(data: VideoRequest):
    transcript = extract_transcript(data.youtube_url)
    if transcript.startswith("Error"):
        return {"error": transcript}

    notes = generate_notes(transcript, data.subject)
    questions = generate_aptitude_questions(data.subject)
    return {
        "title": f"Notes for {data.subject}",
        "content": notes,
        "questions": questions,
        "topics": [data.subject],
    }
