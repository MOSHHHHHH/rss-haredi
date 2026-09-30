import os
import json
import feedparser
from datetime import datetime

def main():
    list_file = 'list.txt'
    output_dir = 'sample'
    
    # וידוא שתיקיית היעד קיימת
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(list_file):
        print(f"Error: {list_file} not found.")
        return

    # קריאת רשימת הכתובות מתוך הקובץ
    with open(list_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    all_titles_data = []

    for index, url in enumerate(urls):
        try:
            print(f"Fetching: {url}")
            feed = feedparser.parse(url)
            
            # 1. שמירת הקובץ הגולמי של התגובה כטקסט או כנתונים גולמיים
            # ניצור שם קובץ בטוח המבוסס על האינדקס או הדומיין
            raw_filename = os.path.join(output_dir, f"feed_{index}.xml")
            
            # ננסה לשמור את הטקסט המקורי אם קיים ב-feed, אחרת נשמור את המבנה כג'ייסון גולמי
            with open(raw_filename, 'w', encoding='utf-8') as raw_file:
                if hasattr(feed, 'bozo_exception') and feed.bozo:
                    # אם יש בעיות פורמט, נשמור את מה שהתקבל
                    raw_file.write(str(feed.entries))
                else:
                    # נכתוב את המידע שפארסר הביא
                    raw_file.write(str(feed))

            # 2. איסוף כותרות, לינקים ושעה מתוך הרשומות
            for entry in feed.entries:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '')
                
                # ניסיון לחלץ תאריך ושעה בפורמט תקני
                published = entry.get('published', entry.get('updated', datetime.now().isoformat()))
                
                all_titles_data.append({
                    "title": title,
                    "link": link,
                    "time": published,
                    "source_url": url
                })
                
        except Exception as e:
            print(f"Failed to process {url}: {e}")

    # שמירת קובץ הסיכום - כותרות בלבד בפורמט JSON
    summary_path = os.path.join(output_dir, "titles_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as json_file:
        json.dump(all_titles_data, json_file, ensure_ascii=False, indent=4)
    
    print("RSS fetching and processing completed successfully.")

if __name__ == "__main__":
    main()
