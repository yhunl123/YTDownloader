import os
import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal

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
            # [수정] 화질 저하 원인이던 'extractor_args' 제거 (Web 클라이언트 복귀)
            # 403 방지를 위한 헤더는 유지
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
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
    finished_signal = pyqtSignal(str)
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

        # 2. 클립 모드(커스텀 구간) 설정
        is_clip_mode = self.options.get('mode') == 'clip'
        start_time_str = self.options.get('start_time', '00:00:00')
        end_time_str = self.options.get('end_time', '00:00:00')

        # yt-dlp 옵션 설정
        ydl_opts = {
            'outtmpl': os.path.join(self.options['path'], '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            # [수정] 화질 저하를 유발하는 안드로이드 클라이언트 옵션 제거
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            # 해상도를 최우선으로 정렬
            'format_sort': ['res', 'ext:mp4:m4a', 'codec:h264:aac'],
        }

        if is_clip_mode:
            section_arg = f"*{start_time_str}-{end_time_str}"
            ydl_opts['download_sections'] = [section_arg]
            video_type = "구간 클립"

        fmt = self.options['format']
        quality = self.options['quality']

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
            # [수정] 최고 화질 로직을 가장 강력한 옵션으로 복원
            if quality == '최고':
                # bestvideo+bestaudio를 강제하고, 실패 시 best 사용
                ydl_opts['format'] = "bestvideo+bestaudio/best"
            else:
                height = quality.replace('p', '')
                ydl_opts['format'] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"

            ydl_opts['merge_output_format'] = fmt

        try:
            final_filename = None

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

                filename = ydl.prepare_filename(info)
                if fmt == 'mp3':
                    base, _ = os.path.splitext(filename)
                    final_filename = base + ".mp3"
                else:
                    final_filename = filename

                filesize = info.get('filesize') or info.get('filesize_approx')
                if filesize:
                    size_mb = f"{filesize / (1024 * 1024):.1f}MB"
                else:
                    size_mb = "알 수 없음"

                duration_sec = info.get('duration', 0)
                m, s = divmod(duration_sec, 60)
                h, m = divmod(m, 60)
                duration_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

                if is_clip_mode:
                    display_duration = f"{start_time_str} ~ {end_time_str}"
                else:
                    display_duration = duration_str

                self.info_signal.emit({
                    'title': info.get('title', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': display_duration,
                    'filesize': size_mb,
                    'ext': fmt,
                    'video_type': video_type
                })

                if self.is_stopped: return

                ydl.download([self.url])

            if not self.is_stopped and final_filename:
                self.finished_signal.emit(final_filename)

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