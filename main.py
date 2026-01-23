import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLineEdit, QPushButton, QLabel, QComboBox, QFileDialog,
                             QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt

from utils import load_settings, save_settings, validate_url
from widgets import DownloadItemWidget

class YouTubeDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("YouTube Downloader")
        self.setGeometry(100, 100, 750, 600) # 너비를 조금 늘려서 여유 확보
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")

        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- 상단 입력부 (Grid Layout 사용) ---
        input_grid = QGridLayout()
        input_grid.setSpacing(10)
        # 열(Column) 비율 설정: 입력창(Col 1)이 늘어나도록 설정
        input_grid.setColumnStretch(1, 1)

        # 1. 링크 URL 행
        url_label = QLabel("링크 URL :")
        url_label.setFixedWidth(80)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("")
        self.url_input.setStyleSheet("padding: 5px; background-color: #333; border: 1px solid #555; color: white;")
        self.url_input.returnPressed.connect(self.add_download_task)

        self.btn_input = QPushButton("입력")
        self.btn_input.setFixedWidth(60)
        self.btn_input.setStyleSheet("background-color: #444; padding: 5px;")
        self.btn_input.clicked.connect(self.add_download_task)

        lbl_fmt = QLabel("파일 형식")
        lbl_fmt.setAlignment(Qt.AlignCenter)
        self.combo_format = QComboBox()
        self.combo_format.addItems(["mp4", "mkv", "mp3"])
        self.combo_format.setCurrentIndex(self.settings.get('format_index', 0))
        self.combo_format.setStyleSheet("background-color: #333; color: white; padding: 3px;")
        self.combo_format.setFixedWidth(80)

        # Grid 배치 (Row 0)
        input_grid.addWidget(url_label, 0, 0)
        input_grid.addWidget(self.url_input, 0, 1)
        input_grid.addWidget(self.btn_input, 0, 2)
        input_grid.addWidget(lbl_fmt, 0, 3)
        input_grid.addWidget(self.combo_format, 0, 4)

        # 2. 저장 경로 행
        path_label = QLabel("저장 경로 :")
        path_label.setFixedWidth(80)
        self.path_input = QLineEdit()
        self.path_input.setText(self.settings.get('save_path', ''))
        self.path_input.setStyleSheet("padding: 5px; background-color: #333; border: 1px solid #555; color: white;")

        self.btn_find = QPushButton("찾기")
        self.btn_find.setFixedWidth(60)
        self.btn_find.setStyleSheet("background-color: #444; padding: 5px;")
        self.btn_find.clicked.connect(self.select_directory)

        lbl_quality = QLabel("화질")
        lbl_quality.setAlignment(Qt.AlignCenter)
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["최고", "1080p", "720p", "480p", "360p"])
        self.combo_quality.setCurrentIndex(self.settings.get('quality_index', 0))
        self.combo_quality.setStyleSheet("background-color: #333; color: white; padding: 3px;")
        self.combo_quality.setFixedWidth(80)

        # Grid 배치 (Row 1)
        input_grid.addWidget(path_label, 1, 0)
        input_grid.addWidget(self.path_input, 1, 1)
        input_grid.addWidget(self.btn_find, 1, 2)
        input_grid.addWidget(lbl_quality, 1, 3)
        input_grid.addWidget(self.combo_quality, 1, 4)

        main_layout.addLayout(input_grid)

        # 구분선
        line = QLabel()
        line.setStyleSheet("border-top: 1px solid #555; margin-top: 5px; margin-bottom: 5px;")
        line.setFixedHeight(1)
        main_layout.addWidget(line)

        # 3. 리스트 헤더
        header_frame = QWidget()
        header_frame.setStyleSheet("border: 1px solid #777; background-color: #2e2e2e;")
        header_layout = QHBoxLayout(header_frame)

        lbl_h1 = QLabel("영상 썸네일")
        lbl_h1.setAlignment(Qt.AlignCenter)
        lbl_h2 = QLabel("영상 제목")
        lbl_h2.setAlignment(Qt.AlignCenter)
        lbl_h3 = QLabel("영상 길이 - 용량 - 파일 형식 - 화질")
        lbl_h3.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(lbl_h1, 1)
        header_layout.addWidget(lbl_h2, 2)
        header_layout.addWidget(lbl_h3, 2)
        main_layout.addWidget(header_frame)

        # 4. 다운로드 리스트 (스크롤 영역)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(5)

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area)

    def select_directory(self):
        path = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.path_input.text())
        if path:
            self.path_input.setText(path)

    def add_download_task(self):
        url = self.url_input.text().strip()

        if not url:
            return

        if not validate_url(url):
            QMessageBox.warning(self, "오류", "유효하지 않은 유튜브 링크입니다.")
            return

        save_path = self.path_input.text().strip()
        if not save_path:
            save_path = os.path.join(os.getcwd(), "download")
            self.path_input.setText(save_path)

        try:
            os.makedirs(save_path, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"경로를 생성할 수 없습니다.\n{e}")
            return

        current_options = {
            'path': save_path,
            'format': self.combo_format.currentText(),
            'quality': self.combo_quality.currentText()
        }

        item_widget = DownloadItemWidget(url, current_options)
        item_widget.remove_requested.connect(self.remove_item)

        self.list_layout.insertWidget(0, item_widget)

        self.url_input.clear()
        self.save_current_settings()

    def remove_item(self, widget):
        widget.stop_download()
        self.list_layout.removeWidget(widget)
        widget.deleteLater()

    def save_current_settings(self):
        new_settings = {
            "save_path": self.path_input.text(),
            "format_index": self.combo_format.currentIndex(),
            "quality_index": self.combo_quality.currentIndex()
        }
        save_settings(new_settings)

    def closeEvent(self, event):
        self.save_current_settings()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloaderApp()
    window.show()
    sys.exit(app.exec_())