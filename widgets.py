import requests
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QProgressBar, QMenu, QAction)
from PyQt5.QtGui import QPixmap, QImage, QCursor
from PyQt5.QtCore import Qt, pyqtSignal
from downloader import DownloadWorker

class DownloadItemWidget(QWidget):
    remove_requested = pyqtSignal(QWidget) # 삭제 요청 신호

    def __init__(self, url, settings):
        super().__init__()
        self.url = url
        self.settings = settings
        self.worker = None
        self.init_ui()
        self.start_download()

    def init_ui(self):
        self.setFixedHeight(100)
        self.setStyleSheet("background-color: #2b2b2b; border: 1px solid #3e3e3e; border-radius: 5px;")

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 1. 썸네일 영역
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(120, 68)
        self.thumb_label.setStyleSheet("background-color: black; border: none;")
        self.thumb_label.setScaledContents(True)
        layout.addWidget(self.thumb_label)

        # 2. 정보 영역
        info_layout = QVBoxLayout()

        self.title_label = QLabel("정보 불러오는 중...")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; border: none;")
        info_layout.addWidget(self.title_label)

        self.meta_label = QLabel(f"준비 중... | {self.settings['format']}")
        self.meta_label.setStyleSheet("color: #aaaaaa; font-size: 12px; border: none;")
        info_layout.addWidget(self.meta_label)

        # 프로그레스 바
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(10)
        self.pbar.setStyleSheet("""
            QProgressBar { border: none; background-color: #444; border-radius: 5px; }
            QProgressBar::chunk { background-color: #3498db; border-radius: 5px; }
        """)
        info_layout.addWidget(self.pbar)

        layout.addLayout(info_layout)
        self.setLayout(layout)

        # 우클릭 메뉴 정책 설정
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def start_download(self):
        self.pbar.setValue(0)
        self.worker = DownloadWorker(self.url, self.settings)
        self.worker.info_signal.connect(self.update_info)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def update_info(self, info):
        self.title_label.setText(info['title'])
        self.meta_label.setText(f"{info['duration']} | {info['ext']} | {self.settings['quality']}")

        # 썸네일 비동기 로드
        try:
            image_data = requests.get(info['thumbnail']).content
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.thumb_label.setPixmap(pixmap)
        except:
            pass

    def update_progress(self, value, msg):
        self.pbar.setValue(int(value))
        if value < 100:
            self.meta_label.setText(f"{msg} ({value:.1f}%)")

    def on_finished(self):
        self.pbar.setValue(100)
        self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }") # 완료 시 초록색
        self.meta_label.setText("다운로드 완료")
        self.worker = None

    def on_error(self, err_msg):
        self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }") # 에러 시 빨간색
        self.meta_label.setText(f"오류: {err_msg}")
        self.worker = None

    def stop_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.meta_label.setText("다운로드 중지됨")

    def retry_download(self):
        if not (self.worker and self.worker.isRunning()):
            self.start_download()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #555; }
        """)

        copy_action = QAction("영상 URL 복사", self)
        stop_action = QAction("다운로드 중지", self)
        retry_action = QAction("재시도", self)
        delete_action = QAction("항목 삭제", self)

        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.url))
        stop_action.triggered.connect(self.stop_download)
        retry_action.triggered.connect(self.retry_download)
        delete_action.triggered.connect(lambda: self.remove_requested.emit(self))

        menu.addAction(copy_action)
        menu.addAction(stop_action)
        menu.addAction(retry_action)
        menu.addSeparator()
        menu.addAction(delete_action)

        menu.exec_(self.mapToGlobal(pos))