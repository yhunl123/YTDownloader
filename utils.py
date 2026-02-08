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
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|shorts/|clip/|.+\?v=)?([^&=%\?]+)')
    match = re.match(youtube_regex, url)
    return match is not None

# --- 추가된 시간 관련 함수 ---
def seconds_to_hms(seconds):
    """초를 HH:MM:SS 문자열로 변환"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

def hms_to_seconds(hms_str):
    """HH:MM:SS 문자열을 초(float)로 변환"""
    try:
        parts = hms_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return 0
    except:
        return 0