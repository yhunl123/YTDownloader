import os
import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal

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

        # 2. 옵션 설정 (로그 억제 포함)
        ydl_opts = {
            'outtmpl': os.path.join(self.options['path'], '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
            'quiet': True,           # 콘솔 로그 억제 (딜레이 체감 감소)
            'no_warnings': True,     # 경고 메시지 억제
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
                # 메타데이터 추출
                info = ydl.extract_info(self.url, download=False)

                filename = ydl.prepare_filename(info)
                if fmt == 'mp3':
                    base, _ = os.path.splitext(filename)
                    final_filename = base + ".mp3"
                else:
                    final_filename = filename

                # 용량 계산 (클립은 용량 정보가 없을 수 있음)
                filesize = info.get('filesize')
                if not filesize:
                    filesize = info.get('filesize_approx') # 예상 용량 시도

                if filesize:
                    size_mb = f"{filesize / (1024 * 1024):.1f}MB"
                else:
                    size_mb = "알 수 없음"

                # 시간 포맷팅 (hh:mm:ss)
                duration_sec = info.get('duration', 0)
                m, s = divmod(duration_sec, 60)
                h, m = divmod(m, 60)
                duration_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

                self.info_signal.emit({
                    'title': info.get('title', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': duration_str,
                    'filesize': size_mb,
                    'ext': fmt,
                    'video_type': video_type
                })

                if self.is_stopped: return

                # 다운로드 시작
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
                # 일반적인 진행률 가져오기
                p_str = d.get('_percent_str', '').replace('%', '')

                if p_str:
                    progress = float(p_str)
                else:
                    # 클립 등에서 퍼센트 정보가 없을 경우 수동 계산
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