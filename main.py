import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLineEdit, QPushButton, QLabel, QComboBox, QFileDialog,
                             QScrollArea, QMessageBox, QMenu, QAction, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QEvent, QObject

from utils import load_settings, save_settings, validate_url, load_history, save_history, seconds_to_hms, hms_to_seconds
from widgets import DownloadItemWidget
from downloader import MetadataWorker

class YouTubeDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.meta_worker = None
        self.current_video_duration = 0 # 현재 입력된 URL 영상의 총 길이(초)
        self.init_ui()
        self.restore_history_items()

    def init_ui(self):
        self.setWindowTitle("YouTube Downloader")
        self.setGeometry(100, 100, 750, 650)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- 상단 입력부 (Grid Layout) ---
        input_grid = QGridLayout()
        input_grid.setSpacing(10)
        input_grid.setColumnStretch(1, 1) # 두 번째 컬럼(입력창)이 늘어나도록

        # [Row 0] 저장 경로 (위로 이동됨)
        path_label = QLabel("저장 경로 :")
        path_label.setFixedWidth(80)
        self.path_input = QLineEdit()
        self.path_input.setText(self.settings.get('save_path', ''))
        self.path_input.setStyleSheet("padding: 5px; background-color: #333; border: 1px solid #555; color: white;")

        self.btn_find = QPushButton("찾기")
        self.btn_find.setFixedWidth(60)
        self.btn_find.setStyleSheet("background-color: #444; padding: 5px;")
        self.btn_find.clicked.connect(self.select_directory)

        # 화질/형식은 이제 아래쪽이나 다른 곳에 배치하는게 좋지만, 기존 유지하며 위치만 조정
        lbl_quality = QLabel("화질")
        lbl_quality.setAlignment(Qt.AlignCenter)
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["최고", "1080p", "720p", "480p", "360p"])
        self.combo_quality.setCurrentIndex(self.settings.get('quality_index', 0))
        self.combo_quality.setStyleSheet("background-color: #333; color: white; padding: 3px;")
        self.combo_quality.setFixedWidth(80)

        input_grid.addWidget(path_label, 0, 0)
        input_grid.addWidget(self.path_input, 0, 1)
        input_grid.addWidget(self.btn_find, 0, 2)
        input_grid.addWidget(lbl_quality, 0, 3)
        input_grid.addWidget(self.combo_quality, 0, 4)

        # [Row 1] 모드 선택 (라디오 버튼)
        mode_label = QLabel("모드 :")
        mode_layout = QHBoxLayout()
        self.rb_normal = QRadioButton("일반 모드")
        self.rb_clip = QRadioButton("클립 모드")
        self.rb_normal.setChecked(True) # 기본값

        # 스타일
        rb_style = "QRadioButton { color: white; } QRadioButton::indicator:checked { background-color: #3498db; border: 2px solid white; border-radius: 6px; }"
        self.rb_normal.setStyleSheet(rb_style)
        self.rb_clip.setStyleSheet(rb_style)

        self.btn_group = QButtonGroup()
        self.btn_group.addButton(self.rb_normal)
        self.btn_group.addButton(self.rb_clip)
        self.btn_group.buttonToggled.connect(self.toggle_clip_ui)

        mode_layout.addWidget(self.rb_normal)
        mode_layout.addWidget(self.rb_clip)
        mode_layout.addStretch(1)

        input_grid.addWidget(mode_label, 1, 0)
        input_grid.addLayout(mode_layout, 1, 1, 1, 4) # Span across columns

        # [Row 2] 링크 URL (아래로 이동됨)
        url_label = QLabel("링크 URL :")
        url_label.setFixedWidth(80)
        self.url_input = QLineEdit()
        self.url_input.setStyleSheet("padding: 5px; background-color: #333; border: 1px solid #555; color: white;")
        self.url_input.returnPressed.connect(self.add_download_task)
        # Focus Out 이벤트 필터 설치
        self.url_input.installEventFilter(self)

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

        input_grid.addWidget(url_label, 2, 0)
        input_grid.addWidget(self.url_input, 2, 1)
        input_grid.addWidget(self.btn_input, 2, 2)
        input_grid.addWidget(lbl_fmt, 2, 3)
        input_grid.addWidget(self.combo_format, 2, 4)

        main_layout.addLayout(input_grid)

        # [Row 3] 시간 입력 (클립 모드용, 초기에는 숨김)
        self.time_widget = QWidget()
        time_layout = QHBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)

        lbl_start = QLabel("시작 시간 :")
        self.input_start = QLineEdit("00:00:00")
        self.input_start.setFixedWidth(100)
        self.input_start.setAlignment(Qt.AlignCenter)
        self.input_start.setStyleSheet("padding: 5px; background-color: #333; border: 1px solid #555; color: white;")

        lbl_tilde = QLabel("~")
        lbl_tilde.setAlignment(Qt.AlignCenter)

        lbl_end = QLabel("종료 시간 :")
        self.input_end = QLineEdit("00:00:00")
        self.input_end.setFixedWidth(100)
        self.input_end.setAlignment(Qt.AlignCenter)
        self.input_end.setStyleSheet("padding: 5px; background-color: #333; border: 1px solid #555; color: white;")

        # 종료 시간 변경 시 유효성 검사 연결
        self.input_end.editingFinished.connect(self.validate_end_time)

        time_layout.addWidget(lbl_start)
        time_layout.addWidget(self.input_start)
        time_layout.addWidget(lbl_tilde)
        time_layout.addWidget(lbl_end)
        time_layout.addWidget(self.input_end)
        time_layout.addStretch(1)

        main_layout.addWidget(self.time_widget)
        self.time_widget.setVisible(False) # 초기 숨김

        # 구분선
        line = QLabel()
        line.setStyleSheet("border-top: 1px solid #555; margin-top: 5px; margin-bottom: 5px;")
        line.setFixedHeight(1)
        main_layout.addWidget(line)

        # 4. 다운로드 리스트
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
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
        self.list_container.setStyleSheet("background-color: #222;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(0)
        self.list_layout.setContentsMargins(0,0,0,0)

        self.scroll_area.setWidget(self.list_container)
        self.scroll_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scroll_area.customContextMenuRequested.connect(self.show_list_context_menu)

        main_layout.addWidget(self.scroll_area)

    def toggle_clip_ui(self):
        """라디오 버튼 토글 시 UI 변경"""
        is_clip = self.rb_clip.isChecked()
        self.time_widget.setVisible(is_clip)

        # 클립 모드로 전환됐는데 URL이 이미 있다면 메타데이터 로드 시도
        if is_clip and self.url_input.text().strip():
            self.fetch_metadata(self.url_input.text().strip())

    def eventFilter(self, source, event):
        """URL 입력창 Focus Out 이벤트 감지"""
        if source == self.url_input and event.type() == QEvent.FocusOut:
            if self.rb_clip.isChecked(): # 클립 모드일 때만
                url = self.url_input.text().strip()
                if url:
                    self.fetch_metadata(url)
        return super().eventFilter(source, event)

    def fetch_metadata(self, url):
        """메타데이터 가져오기 (비동기)"""
        if not validate_url(url): return

        # 중복 실행 방지 or 기존 작업 중단 로직이 필요할 수 있으나 여기선 간단히
        self.meta_worker = MetadataWorker(url)
        self.meta_worker.info_fetched.connect(self.on_metadata_fetched)
        self.meta_worker.start()

    def on_metadata_fetched(self, info):
        """메타데이터 로드 완료 시 시간 설정"""
        duration = info.get('duration', 0)
        self.current_video_duration = duration # 저장해둠 (검증용)

        # 시작 시간 00:00:00
        self.input_start.setText("00:00:00")

        # 종료 시간 = 영상 길이
        end_time_str = seconds_to_hms(duration)
        self.input_end.setText(end_time_str)

    def validate_end_time(self):
        """종료 시간이 영상 길이보다 길면 수정"""
        text = self.input_end.text()
        user_seconds = hms_to_seconds(text)

        if self.current_video_duration > 0 and user_seconds > self.current_video_duration:
            corrected_time = seconds_to_hms(self.current_video_duration)
            self.input_end.setText(corrected_time)
            QMessageBox.information(self, "알림", f"종료 시간이 영상 길이를 초과하여\n영상 끝 시간({corrected_time})으로 조정되었습니다.")

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

        # 중복 방지
        for i in range(self.list_layout.count()):
            widget = self.list_layout.itemAt(i).widget()
            if widget and isinstance(widget, DownloadItemWidget):
                if widget.url == url and not widget.is_completed:
                    QMessageBox.warning(self, "알림", "이미 리스트에 있는 영상입니다.")
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

        # 옵션 수집
        mode = "clip" if self.rb_clip.isChecked() else "normal"
        current_options = {
            'path': save_path,
            'format': self.combo_format.currentText(),
            'quality': self.combo_quality.currentText(),
            'mode': mode
        }

        if mode == "clip":
            # 시간 검증 한 번 더 수행
            self.validate_end_time()
            current_options['start_time'] = self.input_start.text()
            current_options['end_time'] = self.input_end.text()

        item_widget = DownloadItemWidget(url, current_options)
        item_widget.remove_requested.connect(self.remove_item)
        item_widget.cleanup_requested.connect(self.clear_finished_items)

        self.list_layout.insertWidget(0, item_widget)
        self.url_input.clear()

        # 입력 후 시간 초기화
        if mode == "clip":
            self.input_start.setText("00:00:00")
            self.input_end.setText("00:00:00")
            self.current_video_duration = 0

    def remove_item(self, widget):
        widget.stop_download()
        self.list_layout.removeWidget(widget)
        widget.deleteLater()

    def show_list_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #555; }
        """)
        clear_action = QAction("완료된 항목 전체 삭제", self)
        clear_action.triggered.connect(self.clear_finished_items)
        menu.addAction(clear_action)
        menu.exec_(self.scroll_area.mapToGlobal(pos))

    def clear_finished_items(self):
        for i in range(self.list_layout.count() - 1, -1, -1):
            widget = self.list_layout.itemAt(i).widget()
            if widget and isinstance(widget, DownloadItemWidget):
                if widget.is_completed:
                    self.remove_item(widget)

    def restore_history_items(self):
        history = load_history()
        for data in reversed(history):
            item_widget = DownloadItemWidget(data['url'], data['settings'], restore_data=data)
            item_widget.remove_requested.connect(self.remove_item)
            item_widget.cleanup_requested.connect(self.clear_finished_items)
            self.list_layout.insertWidget(0, item_widget)

    def closeEvent(self, event):
        new_settings = {
            "save_path": self.path_input.text(),
            "format_index": self.combo_format.currentIndex(),
            "quality_index": self.combo_quality.currentIndex()
        }
        save_settings(new_settings)

        history_data = []
        for i in range(self.list_layout.count()):
            widget = self.list_layout.itemAt(i).widget()
            if widget and isinstance(widget, DownloadItemWidget):
                history_data.append(widget.get_state())
                widget.stop_download()

        save_history(history_data)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloaderApp()
    window.show()
    sys.exit(app.exec_())