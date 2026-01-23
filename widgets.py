import requests
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QProgressBar, QMenu, QAction, QApplication) # QApplication 추가
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from downloader import DownloadWorker

class DownloadItemWidget(QWidget):
    remove_requested = pyqtSignal(QWidget)

    def __init__(self, url, settings, restore_data=None):
        super().__init__()
        self.url = url
        self.settings = settings
        self.worker = None
        self.is_completed = False
        self.restore_data = restore_data # 복구할 데이터가 있는지 확인

        self.init_ui()

        if self.restore_data:
            self.restore_state()
        else:
            self.start_download()

    def init_ui(self):
        self.setFixedHeight(100)
        # 하단 테두리(border-bottom)를 추가하여 구분선 효과 구현
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b; 
                border-bottom: 1px solid #555; 
            }
        """)

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
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        info_layout.addWidget(self.title_label)

        self.meta_label = QLabel(f"준비 중... | {self.settings['format']}")
        self.meta_label.setStyleSheet("color: #aaaaaa; font-size: 12px; border: none; background: transparent;")
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

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def restore_state(self):
        """저장된 상태로 위젯 복구"""
        data = self.restore_data
        self.title_label.setText(data.get('title', 'Unknown'))
        self.meta_label.setText(data.get('meta_text', ''))

        # 완료 상태 복구
        if data.get('is_completed', False):
            self.pbar.setValue(100)
            self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
            self.is_completed = True
        else:
            # 완료되지 않았던 항목은 '중단됨' 상태로 표시 (자동 재시작 방지)
            self.pbar.setValue(int(data.get('progress', 0)))
            self.meta_label.setText("중단됨 (이전 세션)")
            self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #e67e22; }")

        # 썸네일 로드 (URL이 있다면)
        thumb_url = data.get('thumbnail_url', '')
        if thumb_url:
            try:
                # 썸네일 로딩은 UI 멈춤 방지를 위해 생략하거나 스레드 처리 권장되나,
                # 여기서는 간단히 복구 시도만 함.
                # 실제로는 로컬 캐싱이 없으면 다시 받아야 함.
                pass
            except:
                pass

    def get_state(self):
        """현재 상태를 딕셔너리로 반환 (저장용)"""
        return {
            'url': self.url,
            'settings': self.settings,
            'title': self.title_label.text(),
            'meta_text': self.meta_label.text(),
            'progress': self.pbar.value(),
            'is_completed': self.is_completed,
            'thumbnail_url': '' # 썸네일 URL은 worker 정보에 있어서 여기선 생략 (필요 시 보완)
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
        self.meta_label.setText(f"{info['duration']} | {info['ext']} | {self.settings['quality']}")
        self.current_thumbnail_url = info['thumbnail']

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
        self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
        self.meta_label.setText("다운로드 완료")
        self.worker = None
        self.is_completed = True

    def on_error(self, err_msg):
        self.pbar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
        self.meta_label.setText(f"오류: {err_msg}")
        self.worker = None

    def stop_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.meta_label.setText("다운로드 중지됨")

    def retry_download(self):
        # 이미 실행 중이면 무시
        if self.worker and self.worker.isRunning():
            return
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

        # 버그 수정: QApplication.clipboard() 사용
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