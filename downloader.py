import os
import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal
from yt_dlp.utils import sanitize_filename
from utils import hms_to_seconds # utils에서 시간 변환 함수 가져오기

# --- 메타데이터 워커 ---
class MetadataWorker(QThread):
    info_fetched = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                duration = info.get('duration', 0)
                self.info_fetched.emit({'duration': duration, 'title': info.get('title')})
        except Exception as e:
            self.error_occurred.emit(str(e))

# --- 다운로드 워커 ---
class DownloadWorker(QThread):
    progress_signal = pyqtSignal(float, str)
    finished_signal = pyqtSignal(str, str) # [수정] (파일경로, 파일크기) 전달
    error_signal = pyqtSignal(str)
    info_signal = pyqtSignal(dict)

    def __init__(self, url, options):
        super().__init__()
        self.url = url
        self.options = options
        self.is_stopped = False

    def run(self):
        # 1. 영상 유형 판별
        if "clip/" in self.url:
            video_type = "클립"
        elif "shorts/" in self.url:
            video_type = "쇼츠"
        else:
            video_type = "일반"

        # 2. 옵션 값 가져오기
        is_clip_mode = self.options.get('mode') == 'clip'
        start_time_str = self.options.get('start_time', '00:00:00')
        end_time_str = self.options.get('end_time', '00:00:00')
        save_path = self.options['path']
        fmt = self.options['format']
        quality = self.options['quality']

        # 3. 메타데이터 추출용 기본 옵션
        extract_opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
        }

        try:
            final_filename = None

            # --- [Step 1] 메타데이터 추출 및 파일명 결정 ---
            with yt_dlp.YoutubeDL(extract_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

                title = info.get('title', 'video')
                safe_title = sanitize_filename(title)
                ext = 'mp3' if fmt == 'mp3' else fmt

                if is_clip_mode:
                    base_name = f"{safe_title}_clip"
                    video_type = "구간 클립"
                else:
                    base_name = safe_title

                filename_candidate = f"{base_name}.{ext}"
                full_path_candidate = os.path.join(save_path, filename_candidate)

                counter = 1
                while os.path.exists(full_path_candidate):
                    filename_candidate = f"{base_name} ({counter}).{ext}"
                    full_path_candidate = os.path.join(save_path, filename_candidate)
                    counter += 1

                final_save_name_no_ext = os.path.splitext(full_path_candidate)[0]

            # --- [Step 2] 실제 다운로드 옵션 설정 ---
            ydl_opts = {
                'outtmpl': f"{final_save_name_no_ext}.%(ext)s",
                'progress_hooks': [self.progress_hook],
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                'format_sort': ['res', 'ext:mp4:m4a', 'codec:h264:aac'],
            }

            # [핵심 수정] 클립 모드일 때 download_ranges 사용 (가장 정확한 방법)
            if is_clip_mode:
                start_sec = hms_to_seconds(start_time_str)
                end_sec = hms_to_seconds(end_time_str)

                # yt-dlp 콜백 함수 정의
                def download_range_func(info, ydl):
                    return [{'start_time': start_sec, 'end_time': end_sec}]

                ydl_opts['download_ranges'] = download_range_func
                ydl_opts['force_keyframes_at_cuts'] = True # 정확한 컷팅을 위해 필수

            # 포맷 및 화질 설정
            if fmt == 'mp3':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                if quality == '최고':
                    ydl_opts['format'] = "bestvideo+bestaudio/best"
                else:
                    height = quality.replace('p', '')
                    ydl_opts['format'] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"

                ydl_opts['merge_output_format'] = fmt

            # --- [Step 3] 다운로드 실행 ---
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 초기 용량 표시 (예상치)
                filesize = info.get('filesize') or info.get('filesize_approx')
                if filesize:
                    size_mb = f"{filesize / (1024 * 1024):.1f}MB"
                else:
                    size_mb = "계산 중..."

                duration_sec = info.get('duration', 0)
                m, s = divmod(duration_sec, 60)
                h, m = divmod(m, 60)
                duration_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

                if is_clip_mode:
                    display_duration = f"{start_time_str} ~ {end_time_str}"
                else:
                    display_duration = duration_str

                self.info_signal.emit({
                    'title': title,
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': display_duration,
                    'filesize': size_mb,
                    'ext': fmt,
                    'video_type': video_type
                })

                if self.is_stopped: return

                ydl.download([self.url])

                final_filename = full_path_candidate

            # [핵심 수정] 다운로드 완료 후 실제 파일 크기 확인
            final_size_str = "알 수 없음"
            if final_filename and os.path.exists(final_filename):
                size_bytes = os.path.getsize(final_filename)
                final_size_str = f"{size_bytes / (1024 * 1024):.1f}MB"

            if not self.is_stopped and final_filename:
                # 파일 경로와 실제 크기를 함께 전송
                self.finished_signal.emit(final_filename, final_size_str)

        except Exception as e:
            if not self.is_stopped:
                self.error_signal.emit(str(e))

    def progress_hook(self, d):
        if self.is_stopped:
            raise Exception("다운로드 중지됨")

        if d['status'] == 'downloading':
            try:
                p_str = d.get('_percent_str', '').replace('%', '')
                if p_str:
                    progress = float(p_str)
                else:
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    if total > 0:
                        progress = (downloaded / total) * 100
                    else:
                        progress = 0
                self.progress_signal.emit(progress, "다운로드 중...")
            except:
                pass
        elif d['status'] == 'finished':
            self.progress_signal.emit(100, "변환 및 저장 중...")

    def stop(self):
        self.is_stopped = True