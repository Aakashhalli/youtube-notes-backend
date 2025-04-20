from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import google.generativeai as genai
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import re

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# FastAPI app
app = FastAPI()

# CORS configuration (allow all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class YouTubeRequest(BaseModel):
    youtube_url: str
    subject: str

# Utility: clean response text
def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # remove markdown bold
    text = re.sub(r"[^\x00-\x7F]+", "", text)     # remove emojis/non-ASCII
    text = re.sub(r"\n{2,}", "\n", text)          # fix extra line breaks
    return text

# Extract transcript from YouTube
def extract_transcript(youtube_url):
    try:
        video_id = youtube_url.split("v=")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return transcript_text
    except Exception as e:
        return f"Error fetching transcript: {str(e)}"

# Generate study notes
def generate_notes(transcript_text, subject):
    prompt = f"""
    Title: Structured Study Notes on {subject}
    
    As an AI assistant, your task is to generate structured and detailed notes from the transcript of a YouTube video. 
    The notes should be well-formatted and include:
    - Main topics & key concepts (as section headings).
    - Bullet points or numbered lists for explanations.
    - Examples, formulas, or real-world applications (if mentioned in the video).
    - Concise explanations that improve readability.
    
    Here is the transcript of the video:
    {transcript_text}
    """

    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return clean_text(response.text)

# Generate aptitude questions
def generate_aptitude_questions(subject):
    prompt = f"""
    Title: Placement Aptitude Questions for {subject}

    As an AI assistant, generate 5-7 placement-level aptitude questions commonly asked in technical interviews related to {subject}. 
    Ensure the questions cover:
    - Conceptual understanding
    - Problem-solving scenarios
    - Real-world applications
    - Multiple-choice or open-ended questions

    Format the questions properly with numbering.
    """

    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return clean_text(response.text)

# API route
@app.post("/generate")
async def generate_all(data: YouTubeRequest):
    transcript_text = extract_transcript(data.youtube_url)
    
    if "Error" in transcript_text:
        return {"error": transcript_text}
    
    notes = generate_notes(transcript_text, data.subject)
    questions = generate_aptitude_questions(data.subject)

    return {
        "transcript": transcript_text,
        "notes": notes,
        "questions": questions
    }
