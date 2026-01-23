import os
import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal

class DownloadWorker(QThread):
    progress_signal = pyqtSignal(float, str)  # 진행률, 상태 메시지
    finished_signal = pyqtSignal(str)         # 완료 시 최종 파일 경로 전달
    error_signal = pyqtSignal(str)
    info_signal = pyqtSignal(dict)

    def __init__(self, url, options):
        super().__init__()
        self.url = url
        self.options = options
        self.is_stopped = False

    def run(self):
        ydl_opts = {
            'outtmpl': os.path.join(self.options['path'], '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
        }

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
            if quality == '최고':
                ydl_opts['format'] = f"bestvideo+bestaudio/best"
            else:
                height = quality.replace('p', '')
                ydl_opts['format'] = f"bestvideo[height<={height}]+bestaudio/best"

            ydl_opts['merge_output_format'] = fmt

        try:
            final_filename = None

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 1. 메타데이터 추출
                info = ydl.extract_info(self.url, download=False)

                # 파일명 예측
                filename = ydl.prepare_filename(info)
                if fmt == 'mp3':
                    base, _ = os.path.splitext(filename)
                    final_filename = base + ".mp3"
                else:
                    final_filename = filename

                # 용량 계산 (바이트 -> MB)
                filesize = info.get('filesize') or info.get('filesize_approx')
                if filesize:
                    size_mb = f"{filesize / (1024 * 1024):.1f}MB"
                else:
                    size_mb = "용량 미정"

                self.info_signal.emit({
                    'title': info.get('title', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration_string', '00:00'),
                    'filesize': size_mb, # 용량 정보 추가
                    'ext': fmt
                })

                if self.is_stopped: return

                # 2. 다운로드 시작
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
                p = d.get('_percent_str', '0%').replace('%', '')
                self.progress_signal.emit(float(p), "다운로드 중...")
            except:
                pass
        elif d['status'] == 'finished':
            self.progress_signal.emit(100, "변환 및 저장 중...")

    def stop(self):
        self.is_stopped = True