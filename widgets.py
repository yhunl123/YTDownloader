import os
import subprocess
import requests
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QProgressBar, QMenu, QAction, QApplication, QMessageBox)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from downloader import DownloadWorker

class DownloadItemWidget(QWidget):
    remove_requested = pyqtSignal(QWidget)
    cleanup_requested = pyqtSignal()

    def __init__(self, url, settings, restore_data=None):
        super().__init__()
        self.url = url
        self.settings = settings
        self.worker = None
        self.is_completed = False
        self.saved_path = None
        self.restore_data = restore_data

        self.init_ui()

        if self.restore_data:
            self.restore_state()
        else:
            self.start_download()

    def init_ui(self):
        self.setFixedHeight(110)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b; 
                border-bottom: 1px solid #555; 
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # 썸네일
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(120, 68)
        self.thumb_label.setStyleSheet("background-color: black; border: none;")
        self.thumb_label.setScaledContents(True)
        layout.addWidget(self.thumb_label)

        # 정보 영역
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # 1. 제목
        self.title_label = QLabel("정보 불러오는 중...")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        info_layout.addWidget(self.title_label)

        # 2. 메타 정보 (초기값)
        self.meta_label = QLabel(f"00:00:00 | - | {self.settings['format']} | {self.settings['quality']} | -")
        self.meta_label.setStyleSheet("color: #aaaaaa; font-size: 12px; border: none; background: transparent;")
        info_layout.addWidget(self.meta_label)

        # 3. 상태 메시지
        self.status_label = QLabel("대기 중...")
        self.status_label.setStyleSheet("color: #3498db; font-size: 11px; border: none; background: transparent;")
        info_layout.addWidget(self.status_label)

        # 4. 프로그레스 바
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setStyleSheet("""
            QProgressBar { border: none; background-color: #444; border-radius: 4px; }
            QProgressBar::chunk { background-color: #3498db; border-radius: 4px; }
        """)
        info_layout.addWidget(self.pbar)

        layout.addLayout(info_layout)
        self.setLayout(layout)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def restore_state(self):
        data = self.restore_data
        self.title_label.setText(data.get('title', 'Unknown'))
        self.meta_label.setText(data.get('meta_text', ''))
        self.saved_path = data.get('saved_path', None)

        if data.get('is_completed', False):
            self.pbar.setValue(100)
            self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
            self.status_label.setText("다운로드 완료")
            self.status_label.setStyleSheet("color: #2ecc71; font-size: 11px; border: none; background: transparent;")
            self.is_completed = True
        else:
            self.pbar.setValue(int(data.get('progress', 0)))
            self.status_label.setText("중단됨 (이전 세션)")
            self.status_label.setStyleSheet("color: #e67e22; font-size: 11px; border: none; background: transparent;")
            self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #e67e22; }")

    def get_state(self):
        return {
            'url': self.url,
            'settings': self.settings,
            'title': self.title_label.text(),
            'meta_text': self.meta_label.text(),
            'progress': self.pbar.value(),
            'is_completed': self.is_completed,
            'saved_path': self.saved_path
        }

    def start_download(self):
        self.pbar.setValue(0)
        self.is_completed = False
        self.worker = DownloadWorker(self.url, self.settings)
        self.worker.info_signal.connect(self.update_info)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def update_info(self, info):
        self.title_label.setText(info['title'])
        # 영상 길이 - 용량 - 파일 형식 - 화질 - 영상 유형
        meta_text = f"{info['duration']} - {info['filesize']} - {info['ext']} - {self.settings['quality']} - {info['video_type']}"
        self.meta_label.setText(meta_text)

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
            self.status_label.setText(f"{msg} ({value:.1f}%)")

    def on_finished(self, final_path):
        self.pbar.setValue(100)
        self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
        self.status_label.setText("다운로드 완료")
        self.status_label.setStyleSheet("color: #2ecc71; font-size: 11px; border: none; background: transparent;")
        self.saved_path = final_path
        self.worker = None
        self.is_completed = True

    def on_error(self, err_msg):
        self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
        self.status_label.setText(f"오류: {err_msg}")
        self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px; border: none; background: transparent;")
        self.worker = None

    def stop_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.status_label.setText("다운로드 중지됨")

    def retry_download(self):
        if self.worker and self.worker.isRunning():
            return
        self.status_label.setText("재시도 중...")
        self.status_label.setStyleSheet("color: #3498db; font-size: 11px; border: none; background: transparent;")
        self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #3498db; border-radius: 4px; }")
        self.start_download()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #555; }
        """)

        open_loc_action = QAction("파일 위치 열기", self)
        copy_action = QAction("영상 URL 복사", self)
        stop_action = QAction("다운로드 중지", self)
        retry_action = QAction("재시도", self)
        delete_action = QAction("항목 삭제", self)
        cleanup_action = QAction("완료된 항목 전체 삭제", self)

        open_loc_action.triggered.connect(self.open_file_location)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self.url))
        stop_action.triggered.connect(self.stop_download)
        retry_action.triggered.connect(self.retry_download)
        delete_action.triggered.connect(lambda: self.remove_requested.emit(self))
        cleanup_action.triggered.connect(self.cleanup_requested.emit)

        if self.is_completed:
            menu.addAction(open_loc_action)
            menu.addSeparator()

        menu.addAction(copy_action)
        menu.addAction(stop_action)
        menu.addAction(retry_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(cleanup_action)

        menu.exec_(self.mapToGlobal(pos))

    def open_file_location(self):
        if not self.saved_path:
            QMessageBox.warning(self, "알림", "저장된 파일 경로 정보가 없습니다.")
            return

        if os.path.exists(self.saved_path):
            try:
                if os.name == 'nt':
                    subprocess.Popen(['explorer', '/select,', os.path.normpath(self.saved_path)])
                else:
                    folder_path = os.path.dirname(self.saved_path)
                    subprocess.Popen(['xdg-open' if os.name == 'posix' else 'open', folder_path])
            except Exception as e:
                QMessageBox.warning(self, "오류", f"폴더를 여는 중 오류가 발생했습니다.\n{e}")
        else:
            QMessageBox.warning(self, "파일 없음", "파일을 찾을 수 없습니다.")