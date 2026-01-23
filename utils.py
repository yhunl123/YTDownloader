import json
import os
import re

SETTINGS_FILE = 'settings.json'
HISTORY_FILE = 'history.json'

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

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_history(history_data):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"히스토리 저장 실패: {e}")

def validate_url(url):
    # clip/ 경로 추가 및 ID 길이 제한({11})을 해제하고 (+로 변경) 다양한 길이를 허용
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|shorts/|clip/|.+\?v=)?([^&=%\?]+)')
    match = re.match(youtube_regex, url)
    return match is not None