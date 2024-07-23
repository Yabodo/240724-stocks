import os
import streamlit as st
import sqlite3
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from datetime import datetime
import uvicorn
import threading
import time
from streamlit_autorefresh import st_autorefresh
import pygame
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# API Key configuration
API_KEY = os.getenv('API_KEY')
api_key_header = APIKeyHeader(name="X-API-Key")

# Global variable to track the last added news item's ID
last_news_id = 0

def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

# Define the News model
class News(BaseModel):
    title: str
    published: str
    trading_decision: str

# Connect to SQLite database
def get_db_connection():
    conn = sqlite3.connect('news.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Create the news table if it doesn't exist
def create_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            published TEXT NOT NULL,
            trading_decision TEXT NOT NULL
        )
    ''')
    conn.close()

create_table()

# API endpoint to receive news
@app.post("/news")
async def add_news(news: News, api_key: str = Depends(get_api_key)):
    global last_news_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO news (title, published, trading_decision)
        VALUES (?, ?, ?)
    ''', (news.title, news.published, news.trading_decision))
    last_news_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"message": "News added successfully"}

# Function to check for new articles
def check_for_new_articles(last_displayed_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) as max_id FROM news')
    result = cursor.fetchone()
    max_id = result['max_id'] if result['max_id'] is not None else 0
    conn.close()
    return max_id > last_displayed_id

# Streamlit interface
def streamlit_app():
    st.title("News Service")

    # Initialize pygame mixer
    pygame.mixer.init()
    try:
        notification_sound = pygame.mixer.Sound('notification.mp3')
    except pygame.error:
        st.error("Failed to load notification sound. Make sure 'notification.mp3' is in the project directory.")
        notification_sound = None

    st.info("To add news, send a POST request to /news with the X-API-Key header.")

    # Add auto-refresh component
    st_autorefresh(interval=5000, key="news_refresh")

    # Initialize session state for last displayed ID
    if 'last_displayed_id' not in st.session_state:
        st.session_state.last_displayed_id = 0

    # Check for new articles
    if check_for_new_articles(st.session_state.last_displayed_id):
        st.warning("New articles have been added!")
        if notification_sound:
            notification_sound.play()  # Play notification sound using pygame

    # Display existing news
    conn = get_db_connection()
    news_items = conn.execute('SELECT * FROM news ORDER BY id DESC').fetchall()
    conn.close()

    for item in news_items:
        st.write(f"**{item['title']}**")
        st.write(f"Published: {item['published']}")
        st.write(f"Trading Decision: {item['trading_decision']}")
        st.write("---")
        st.session_state.last_displayed_id = max(st.session_state.last_displayed_id, item['id'])

# Run both FastAPI and Streamlit
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # Run FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.start()

    # Run Streamlit
    streamlit_app()