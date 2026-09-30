import os
import json
import feedparser
import requests

def main():
    list_path = 'list.txt'
    output_dir = 'sample'
    
    # וידוא שתיקיית היעד קיימת
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(list_path):
        print(f"Error: {list_path} not found.")
        return

    # קריאת רשימת הכתובות מתוך list.txt
    with open(list_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    all_titles_data = []

    for index, url in enumerate(urls, start=1):
        try:
            print(f"Fetching: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # 1. שמירת הקובץ הגולמי
            raw_filename = f"feed_{index}.xml"
            raw_filepath = os.path.join(output_dir, raw_filename)
            with open(raw_filepath, 'w', encoding='utf-8') as raw_file:
                raw_file.write(response.text)

            # 2. ניתוח הפיד באמצעות feedparser כדי לחלץ כותרות, לינקים ושעות
            parsed_feed = feedparser.parse(response.text)
            
            feed_title = parsed_feed.feed.get('title', f'Feed {index}')
            
            for entry in parsed_feed.entries:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '')
                # לקיחת תאריך הפרסום, ואם אינו קיים – שימוש בזמן העדכון או מחרוזת ריקה
                pub_date = entry.get('published', entry.get('updated', ''))
                
                all_titles_data.append({
                    'feed_source': feed_title,
                    'title': title,
                    'link': link,
                    'published_at': pub_date
                })
                
        except Exception as e:
            print(f"Failed to process {url}: {e}")

    # שמירת קובץ ה-JSON המסכם את כל הכותרות
    json_filepath = os.path.join(output_dir, 'latest_headlines.json')
    with open(json_filepath, 'w', encoding='utf-8') as json_file:
        json.dump(all_titles_data, json_file, ensure_ascii=False, indent=4)
    
    print("RSS fetching and parsing completed successfully.")

if __name__ == '__main__':
    main()
