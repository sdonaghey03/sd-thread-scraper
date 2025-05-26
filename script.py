import requests
from bs4 import BeautifulSoup
import time
import os

# Updated Discord webhook URL
WEBHOOK_URL = 'https://discord.com/api/webhooks/1376570425588322307/OVy9MRF_4N0RxTKSN5aOAy52eNhxPPN5dUNDHln6pQTaXblRw-Cl9X1Jd78v4UP_bx2I'

# URL of the phpBB thread to monitor
THREAD_URL = 'https://forum.eclipse-rp.net/topic/28550-los-santos-county-sheriffs-department'

# File to store the ID of the latest seen post
LATEST_POST_FILE = 'latest_post_id.txt'

def get_latest_post_id():
    if os.path.exists(LATEST_POST_FILE):
        with open(LATEST_POST_FILE, 'r') as file:
            return file.read().strip()
    return None

def save_latest_post_id(post_id):
    with open(LATEST_POST_FILE, 'w') as file:
        file.write(post_id)

def scrape_thread():
    response = requests.get(THREAD_URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    posts = soup.find_all('article', id=lambda x: x and x.startswith('elComment_'))

    post_data = []
    for post in posts:
        post_id = post['id'].replace('elComment_', '')

        username_tag = post.find('a', class_='ipsType_break')
        username = username_tag.get_text(strip=True) if username_tag else 'Unknown'

        time_tag = post.find('time')
        timestamp = time_tag['datetime'] if time_tag and time_tag.has_attr('datetime') else None

        content_div = post.find('div', class_='ipsContained')
        if content_div:
            full_text = content_div.get_text(separator=' ', strip=True)
            full_text = full_text.replace('ReportPosted', '').strip()
            summary = full_text[:200] + ('...' if len(full_text) > 200 else '')

            img_tag = content_div.find('img')
            img_url = img_tag['src'] if img_tag else None

            post_data.append((post_id, username, timestamp, summary, img_url))
    return [post_data[4]]

def send_to_discord(username, timestamp, summary, img_url):
    embed = {
        "title": "📢 New Reply in the ECRP Faction Thread",
        "author": {
            "name": username
        },
        "description": summary,
        "timestamp": timestamp,
        "color": 3447003
    }
    if img_url:
        embed["image"] = {"url": img_url}
    data = {"embeds": [embed]}
    response = requests.post(WEBHOOK_URL, json=data)
    if response.status_code in [200, 204]:
        print("✅ Embed sent successfully.")
    else:
        print(f"❌ Failed to send embed. Status code: {response.status_code}")

def main():
    while True:
        latest_post_id = get_latest_post_id()
        post_data = scrape_thread()

        new_replies = []
        for post_id, username, timestamp, summary, img_url in post_data:
            if post_id == latest_post_id:
                break
            new_replies.append((post_id, username, timestamp, summary, img_url))

        if new_replies:
            for post_id, username, timestamp, summary, img_url in reversed(new_replies):
                send_to_discord(username, timestamp, summary, img_url)
                save_latest_post_id(post_id)

        time.sleep(300)

if __name__ == "__main__":
    main()
