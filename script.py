import requests
from bs4 import BeautifulSoup
import psycopg2
import time
import os

# ✅ Updated Discord webhook URL
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Base thread URL
THREAD_URL = 'https://forum.eclipse-rp.net/topic/28550-los-santos-county-sheriffs-department'

# File to store the ID of the latest seen post
LATEST_POST_FILE = 'latest_post_id.txt'

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT")
    )

def get_latest_post_id():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS post_tracker (id SERIAL PRIMARY KEY, latest_post_id TEXT);")
    cur.execute("SELECT latest_post_id FROM post_tracker ORDER BY id DESC LIMIT 1;")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None


def save_latest_post_id(post_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO post_tracker (latest_post_id) VALUES (%s);", (post_id,))
    conn.commit()
    cur.close()
    conn.close()

def scrape_thread():
    post_data = []
    page = 1

    while True:
        print(f"Scraping page {page}...")
        response = requests.get(f"{THREAD_URL}/page/{page}")
        print(f"Response status code: {response.status_code}")
        soup = BeautifulSoup(response.content, 'html.parser')
        print(f"Parsing HTML content for {page}...")

        if response.url != f"{THREAD_URL}/page/{page}":
            print(f"End of pages, stopping scrape.")
            break
        
        posts = soup.find_all('article', id=lambda x: x and x.startswith('elComment_'))
        if not posts:
            break

        for post in posts:
            post_id = post['id'].replace('elComment_', '')

            username_tag = post.find('a', class_='ipsType_break')
            username = username_tag.get_text(strip=True) if username_tag else 'Unknown'

            time_tag = post.find('time')
            timestamp = time_tag['datetime'] if time_tag and time_tag.has_attr('datetime') else None

            content_div = post.find('div', class_='ipsComment_content')
            if content_div:
                full_text = content_div.get_text(separator=' ', strip=True)
                full_text = full_text.replace('ReportPosted', '').strip()
                summary = full_text[:200] + ('...' if len(full_text) > 200 else '')

                img_tag = content_div.find('img')
                img_url = img_tag['src'] if img_tag else None

                post_url = f"{THREAD_URL}/?do=findComment&comment={post_id}"

                post_data.append((post_id, username, timestamp, summary, img_url, post_url))
        
        page += 1

    return list(reversed(post_data))  # Newest posts first

def send_to_discord(username, timestamp, summary, img_url, post_url):
    embed = {
        "title": "📢 New Reply in LS County Sheriff's Thread",
        "author": {
            "name": username
        },
        "description": summary,
        "timestamp": timestamp,
        "color": 3447003,
        "url": post_url
    }
    if img_url:
        embed["image"] = {"url": img_url}
    data = {"embeds": [embed]}
    print(f"Sending embed to {WEBHOOK_URL}...")
    response = requests.post(WEBHOOK_URL, json=data)
    if response.status_code in [200, 204]:
        print("✅ Embed sent successfully.")
    else:
        print(f"❌ Failed to send embed. Status code: {response.status_code}")

def main():
    while True:
        latest_post_id = get_latest_post_id()
        print(f"Latest post ID: {latest_post_id}")

        post_data = scrape_thread()

        new_replies = []
        for post_id, username, timestamp, summary, img_url, post_url in post_data:
            if post_id == latest_post_id:
                break
            new_replies.append((post_id, username, timestamp, summary, img_url, post_url))

        if new_replies:
            for post_id, username, timestamp, summary, img_url, post_url in reversed(new_replies):
                send_to_discord(username, timestamp, summary, img_url, post_url)
                save_latest_post_id(post_id)
                time.sleep(5)  # Sleep to avoid hitting rate limits

        time.sleep(300)  # Wait 5 minutes

if __name__ == "__main__":
    main()
