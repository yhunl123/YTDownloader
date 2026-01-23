import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLineEdit, QPushButton, QLabel, QComboBox, QFileDialog,
                             QScrollArea, QMessageBox, QMenu, QAction) # QMenu, QAction 추가
from PyQt5.QtCore import Qt

from utils import load_settings, save_settings, validate_url, load_history, save_history
from widgets import DownloadItemWidget

class YouTubeDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.init_ui()
        self.restore_history_items() # 히스토리 복구

    def init_ui(self):
        self.setWindowTitle("YouTube Downloader")
        self.setGeometry(100, 100, 750, 600)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")

        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- 상단 입력부 (Grid Layout) ---
        input_grid = QGridLayout()
        input_grid.setSpacing(10)
        input_grid.setColumnStretch(1, 1)

        # Row 0: URL 입력
        url_label = QLabel("링크 URL :")
        url_label.setFixedWidth(80)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/...")
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

        input_grid.addWidget(url_label, 0, 0)
        input_grid.addWidget(self.url_input, 0, 1)
        input_grid.addWidget(self.btn_input, 0, 2)
        input_grid.addWidget(lbl_fmt, 0, 3)
        input_grid.addWidget(self.combo_format, 0, 4)

        # Row 1: 저장 경로
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

        # --- 헤더 제거됨 (요청사항 2) ---

        # 4. 다운로드 리스트 (스크롤 영역) - 스타일 개선 (음각 효과)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # 음각 효과를 위한 스타일시트 적용
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px inset #2a2a2a;
                background-color: #222;
            }
            QScrollBar:vertical {
                background: #333;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #555;
            }
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background-color: #222;") # 컨테이너 배경색 일치
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(0) # 항목 간 간격 0으로 설정 (widget의 border-bottom이 구분선 역할)
        self.list_layout.setContentsMargins(0,0,0,0)

        self.scroll_area.setWidget(self.list_container)

        # 리스트 영역 우클릭 메뉴 설정
        self.scroll_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scroll_area.customContextMenuRequested.connect(self.show_list_context_menu)

        main_layout.addWidget(self.scroll_area)

    def select_directory(self):
        path = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.path_input.text())
        if path:
            self.path_input.setText(path)

    def add_download_task(self):
        url = self.url_input.text().strip()
        if not url: return

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

        # 새 항목 생성 (복구 데이터 없음)
        item_widget = DownloadItemWidget(url, current_options)
        item_widget.remove_requested.connect(self.remove_item)

        self.list_layout.insertWidget(0, item_widget)
        self.url_input.clear()

    def remove_item(self, widget):
        widget.stop_download()
        self.list_layout.removeWidget(widget)
        widget.deleteLater()

    def show_list_context_menu(self, pos):
        # 다운로드 리스트 전체에 대한 우클릭 메뉴
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #555; }
        """)

        clear_finished_action = QAction("완료된 항목 전체 삭제", self)
        clear_finished_action.triggered.connect(self.clear_finished_items)
        menu.addAction(clear_finished_action)

        menu.exec_(self.scroll_area.mapToGlobal(pos))

    def clear_finished_items(self):
        # 역순으로 순회하며 삭제 (인덱스 문제 방지)
        for i in range(self.list_layout.count() - 1, -1, -1):
            widget = self.list_layout.itemAt(i).widget()
            if widget and isinstance(widget, DownloadItemWidget):
                if widget.is_completed:
                    self.remove_item(widget)

    def restore_history_items(self):
        history = load_history()
        # 저장된 순서대로 복원 (최신이 위로 가도록 하려면 역순으로 insertWidget(0) 하거나,
        # 리스트에 저장될 때 순서를 고려해야 함. 여기선 단순히 append 후 insertWidget(0) 이므로
        # 저장 시 최상단부터 저장했다면, 불러올 때 역순으로 넣어야 원래 순서 유지.
        # 편의상 그냥 순서대로 불러와서 쌓음.

        for data in reversed(history): # 역순 순회하여 insertWidget(0) 시 순서 유지
            item_widget = DownloadItemWidget(data['url'], data['settings'], restore_data=data)
            item_widget.remove_requested.connect(self.remove_item)
            self.list_layout.insertWidget(0, item_widget)

    def closeEvent(self, event):
        # 설정 저장
        new_settings = {
            "save_path": self.path_input.text(),
            "format_index": self.combo_format.currentIndex(),
            "quality_index": self.combo_quality.currentIndex()
        }
        save_settings(new_settings)

        # 히스토리 저장
        history_data = []
        # Layout의 위젯들을 순회하며 상태 저장
        for i in range(self.list_layout.count()):
            widget = self.list_layout.itemAt(i).widget()
            if widget and isinstance(widget, DownloadItemWidget):
                history_data.append(widget.get_state())
                widget.stop_download() # 종료 시 쓰레드 중지

        save_history(history_data)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloaderApp()
    window.show()
    sys.exit(app.exec_())