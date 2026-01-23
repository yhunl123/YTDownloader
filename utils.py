import json
import os
import re

SETTINGS_FILE = 'settings.json'

DEFAULT_SETTINGS = {
    "save_path": os.path.join(os.getcwd(), "download"),
    "format_index": 0,  # 0: mp4, 1: mkv, 2: mp3
    "quality_index": 0  # 0: 최고, 1: 1080p, ...
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"설정 저장 실패: {e}")

def validate_url(url):
    # 유튜브 영상 및 쇼츠 URL 패턴 확인
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|shorts/|.+\?v=)?([^&=%\?]{11})')
    match = re.match(youtube_regex, url)
    return match is not None