import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QHBoxLayout, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow
from pathlib import Path

from chatterly.utils.constants import SESSIONS_DIR
from chatterly.poc.meet.screen import MockMeetScreen

class InterviewCard(QWidget):
    def __init__(self, metadata, on_start):
        super().__init__()
        self.metadata = metadata
        self.on_start = on_start
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel(f"<b>{self.metadata['interview_name']}</b>")
        subtitle = QLabel(f"Role: {self.metadata['role']}")
        start_btn = QPushButton("Start Interview")
        start_btn.clicked.connect(lambda: self.on_start(self.metadata))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(start_btn)
        self.setLayout(layout)
        self.setStyleSheet("border: 1px solid gray; padding: 10px; margin: 5px;")

class PermissionDialog(QMessageBox):
    def __init__(self, on_confirm):
        super().__init__()
        self.setWindowTitle("Permissions Required")
        self.setText("This interview requires access to your microphone and camera.\nDo you want to proceed?")
        self.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.buttonClicked.connect(lambda btn: on_confirm(btn == self.button(QMessageBox.StandardButton.Yes)))


class InterviewPanel(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout()

        for session_dir in Path(SESSIONS_DIR).iterdir():
            if session_dir.is_dir():
                json_files = list(session_dir.glob("*.json"))
                if not json_files:
                    continue
                with open(json_files[0], "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    card = InterviewCard(metadata, self.handle_start)
                    container_layout.addWidget(card)

        container.setLayout(container_layout)
        scroll.setWidget(container)
        layout.addWidget(QLabel("<h1>Available Interview Sessions</h1>"))
        layout.addWidget(scroll)
        self.setLayout(layout)



    def handle_start(self, metadata):
        def on_permission_granted(granted):
            if granted:
                self.popup = QMainWindow()
                self.popup.setWindowTitle("Interview Session")
                self.popup.setCentralWidget(MockMeetScreen(metadata, self.popup))
                self.popup.resize(700, 500)
                self.popup.show()

        dialog = PermissionDialog(on_permission_granted)
        dialog.exec()


    # def handle_start(self, metadata):
    #     def on_permission_granted(granted):
    #         if granted:
    #             meet_screen = MockMeetScreen(metadata,self.stacked_widget)
    #             self.stacked_widget.addWidget(meet_screen)
    #             self.stacked_widget.setCurrentWidget(meet_screen)

    #     dialog = PermissionDialog(on_permission_granted)
    #     dialog.exec()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interview Panel")
        self.resize(600, 400)
        self.stack = QStackedWidget()
        self.panel = InterviewPanel(self.stack)
        self.stack.addWidget(self.panel)

        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
