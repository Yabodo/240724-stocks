# Make sure to install BeautifulSoup and lxml: pip install beautifulsoup4 lxml
import os
import requests
import json
import time
from bs4 import BeautifulSoup
import lxml
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Constants
TRADINGVIEW_URL = os.getenv('TRADINGVIEW_URL')
TRADINGVIEW_BASE = os.getenv('TRADINGVIEW_BASE')
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY')
API_ENDPOINT = os.getenv('API_ENDPOINT')
API_KEY = os.getenv('API_KEY')

anthropic = Anthropic(api_key=CLAUDE_API_KEY)

def fetch_news():
    print("Fetching news")
    response = requests.get(TRADINGVIEW_URL)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching news: {response.status_code}")
        return None

def extract_article_content(story_path):
    full_url = f"{TRADINGVIEW_BASE}{story_path}"
    response = requests.get(full_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'lxml')
        article_content = soup.select_one('article')
        print(article_content)
        if article_content:
            return article_content.get_text().strip()
    return None

def get_trading_decision(article_content):
    print("Analyzing article")
    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        system="Based on the news article, provide a trading decision (buy, sell, or hold) and a brief explanation",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": article_content
                    }
                ]
            }
        ],
        max_tokens=300
    )
    return response.content[0].text

def send_api_request(title, published, trading_decision):
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    data = {
        "title": title,
        "published": published.strftime("%Y-%m-%d"),
        "trading_decision": trading_decision
    }
    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        print(f"API request sent successfully for article: {title}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending API request for article '{title}': {str(e)}")

def main():
    print("Starting stock trading signal bot...")
    last_processed_timestamp = 0
    while True:
        news_data = fetch_news()
        if news_data and 'items' in news_data:
            current_time = datetime.now()
            for item in news_data['items']:
                published_time = datetime.fromtimestamp(item['published'])  # Convert milliseconds to seconds
                if published_time > current_time - timedelta(minutes=15) and item['published'] > last_processed_timestamp:
                    story_path = item['storyPath']
                    article_content = extract_article_content(story_path)
                    if article_content:
                        trading_decision = get_trading_decision(article_content)
                        print(f"News: {item['title']}")
                        print(f"Published: {published_time}")
                        print(f"Trading Decision: {trading_decision}")
                        print("---")
                        
                        # Send API request
                        send_api_request(item['title'], published_time, trading_decision)
                        
                    last_processed_timestamp = item['published']
        time.sleep(15)  # Wait for 15 seconds before fetching news again

if __name__ == "__main__":
    main()