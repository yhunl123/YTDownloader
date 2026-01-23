import os
import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal

class DownloadWorker(QThread):
    progress_signal = pyqtSignal(float, str)  # 진행률, 상태 메시지
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    info_signal = pyqtSignal(dict) # 썸네일, 제목 등 정보 전달

    def __init__(self, url, options):
        super().__init__()
        self.url = url
        self.options = options
        self.is_stopped = False

    def run(self):
        # yt-dlp 옵션 설정
        ydl_opts = {
            'outtmpl': os.path.join(self.options['path'], '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
        }

        # 포맷 및 화질 설정
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
            # 비디오 포맷
            if quality == '최고':
                ydl_opts['format'] = f"bestvideo+bestaudio/best"
            else:
                height = quality.replace('p', '')
                ydl_opts['format'] = f"bestvideo[height<={height}]+bestaudio/best"

            ydl_opts['merge_output_format'] = fmt

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 메타데이터 먼저 추출
                info = ydl.extract_info(self.url, download=False)
                self.info_signal.emit({
                    'title': info.get('title', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration_string', '00:00'),
                    'ext': fmt
                })

                if self.is_stopped: return

                # 다운로드 시작
                ydl.download([self.url])

            if not self.is_stopped:
                self.finished_signal.emit()

        except Exception as e:
            if not self.is_stopped:
                self.error_signal.emit(str(e))

    def progress_hook(self, d):
        if self.is_stopped:
            raise Exception("다운로드 중지됨")

        if d['status'] == 'downloading':
            try:
                p = d.get('_percent_str', '0%').replace('%', '')
                self.progress_signal.emit(float(p), "다운로드 중...")
            except:
                pass
        elif d['status'] == 'finished':
            self.progress_signal.emit(100, "변환 및 저장 중...")

    def stop(self):
        self.is_stopped = True