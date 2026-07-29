import os
import json
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# API Endpoint
API_URL = "https://bingstreams.live/api/streams/live-merged"

# Output directories
OUTPUT_DIR = "output"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def fetch_image(url):
    """URL থেকে ইমেজ ডাউনলোড করার হেল্পার ফাংশন"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Error fetching image {url}: {e}")
    return None

def generate_premium_banner(match):
    """Pillow ব্যবহার করে হোম ও অ্যাওয়ে টিমের লোগো দিয়ে প্রিমিয়াম পোস্টার তৈরি"""
    match_id = match.get("id", "unknown")
    output_path = os.path.join(IMAGE_DIR, f"{match_id}.png")
    
    # ক্যানভাস সাইজ (HD Card Banner)
    width, height = 800, 450
    
    # ডার্ক প্রিমিয়াম ব্যাকগ্রাউন্ড তৈরি
    banner = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    draw = ImageDraw.Draw(banner)
    
    # গ্রেডিয়েন্ট / গ্লাস ইফেক্ট (অপশনাল স্টাইলিং)
    draw.rectangle([0, 0, width, 80], fill=(30, 41, 59, 255)) # টপ বার
    
    # টিম তথ্য
    teams = match.get("teams", {})
    home_badge_url = teams.get("home", {}).get("badge")
    away_badge_url = teams.get("away", {}).get("badge")
    
    home_img = fetch_image(home_badge_url) if home_badge_url else None
    away_img = fetch_image(away_badge_url) if away_badge_url else None
    
    # হোম টিম লোগো প্লেসমেন্ট (বাম পাশে)
    if home_img:
        home_img.thumbnail((200, 200))
        banner.paste(home_img, (120, 130), home_img)
        
    # অ্যাওয়ে টিম লোগো প্লেসমেন্ট (ডান পাশে)
    if away_img:
        away_img.thumbnail((200, 200))
        banner.paste(away_img, (480, 130), away_img)
        
    # VS টেক্সট আঁকা (মাঝখানে)
    draw.text((width // 2, 210), "VS", fill=(239, 68, 68, 255), anchor="mm")
    
    # ক্যাটাগরি ও ম্যাচ টাইটেল টেক্সট
    category = match.get("category", "SPORTS").upper()
    title = match.get("title", "")
    
    draw.text((width // 2, 40), f"• {category} LIVE •", fill=(34, 197, 94, 255), anchor="mm")
    draw.text((width // 2, 380), title[:45], fill=(255, 255, 255, 255), anchor="mm")
    
    # সেভ করা
    banner.convert("RGB").save(output_path, "PNG", quality=90)
    return output_path

def main():
    print("Fetching live streams...")
    try:
        res = requests.get(API_URL, timeout=15)
        data = res.json()
    except Exception as e:
        print(f"Failed to fetch API: {e}")
        return

    if not data.get("success"):
        print("API returned false success")
        return

    matches = data.get("matches", [])
    
    processed_matches = []
    m3u_lines = ["#EXTM3U"]

    for match in matches:
        category = match.get("category", "General")
        title = match.get("title", "Live Stream")
        
        # প্রিমিয়াম পোস্টার জেনারেট
        try:
            banner_file = generate_premium_banner(match)
        except Exception as e:
            print(f"Banner error for {title}: {e}")
            banner_file = match.get("poster")
            
        match["generated_poster"] = banner_file
        processed_matches.append(match)

        # M3U জেনারেট (ইফ্রেমে স্ট্রিম লিংক থাকলে)
        iframes = match.get("iframes", [])
        for idx, iframe in enumerate(iframes):
            stream_url = iframe.get("url")
            server_name = iframe.get("server", f"Stream {idx+1}")
            
            if stream_url:
                m3u_lines.append(
                    f'#EXTINF:-1 tvg-logo="{match.get("thumbnail", "")}" group-title="{category.capitalize()}", {title} ({server_name})'
                )
                m3u_lines.append(stream_url)

    # ১. ক্যাটাগরি অনুযায়ী সাজানো JSON ফাইল সেভ
    categories = {}
    for m in processed_matches:
        cat = m.get("category", "uncategorized")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(m)

    json_output_path = os.path.join(OUTPUT_DIR, "streams.json")
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump({"total": len(processed_matches), "categories": categories, "matches": processed_matches}, f, indent=2, ensure_ascii=False)

    # ২. RAW M3U ফাইল সেভ
    m3u_output_path = os.path.join(OUTPUT_DIR, "playlist.m3u")
    with open(m3u_output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    print("Automation Completed Successfully!")

if __name__ == "__main__":
    main()
