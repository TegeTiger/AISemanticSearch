import streamlit as st
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathlib import Path
import os
from exa_py import Exa
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

# === Load API keys from .env === #
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

EXA_API_KEY = os.getenv("EXA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
exa = Exa(EXA_API_KEY)

# === Helper Functions === #
def is_youtube_url(url):
    return "youtube.com/watch" in url or "youtu.be/" in url

def is_video_url(url):
    return any(domain in url for domain in [
        "youtube.com", "youtu.be", "tiktok.com", "instagram.com", "dailymotion.com"
    ])

def summarize_text_with_gpt(text):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Summarize this:\n\n{text}"}],
            max_tokens=100
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        if "insufficient_quota" in str(e).lower():
            return "[⚠️ OpenAI quota exceeded. Check your billing setup.]"
        return f"[GPT error: {e}]"

def summarize_webpage(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        text_blocks = [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
        if not text_blocks:
            return "[⚠️ No readable text found on this page.]"
        text = " ".join(text_blocks[:10])
        return summarize_text_with_gpt(text)
    except Exception:
        return None

def summarize_youtube(url):
    try:
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
        else:
            return "[Unrecognized YouTube format]"

        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([chunk['text'] for chunk in transcript][:20])
        return summarize_text_with_gpt(text)
    except Exception:
        return None

def get_summary(url):
    if is_youtube_url(url):
        return summarize_youtube(url)
    elif is_video_url(url):
        return None
    else:
        return summarize_webpage(url)

# === Streamlit UI === #
st.set_page_config(page_title="AI Semantic Search", layout="wide")
st.title("🔍 AI-Powered Semantic Search")

query = st.text_input("Enter your search query:", placeholder="e.g. best productivity tools")

if query:
    with st.spinner("Searching with Exa and summarizing results using GPT..."):
        response = exa.search(
            query,
            num_results=5,
            use_autoprompt=True,
            type="neural"
        )

        for result in response.results:
            st.markdown("---")
            st.subheader(result.title)
            st.markdown(f"**URL**: [{result.url}]({result.url})")
            summary = get_summary(result.url)
            st.markdown(f"**Summary:** {summary}")