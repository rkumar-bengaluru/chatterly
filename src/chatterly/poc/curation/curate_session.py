import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QDateEdit, QDialog, QLabel, QSpinBox,
    QHBoxLayout, QScrollArea, QGroupBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QGuiApplication
from functools import partial
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QTextEdit, QSpinBox, QPushButton,
    QMessageBox, QHBoxLayout
)
from PyQt6.QtGui import QGuiApplication
import os 
from chatterly.poc.xttsv2.gen_voice import load_model, gen_voice
from chatterly.utils.constants import SESSIONS_DIR
from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.poc.curation.dialog import QuestionDialog
import base64
import uuid

class InterviewApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interview Session Manager")
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8;
                font-family: Arial;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005fa1;
            }
            QLabel {
                font-weight: bold;
            }
        """)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        screen = QGuiApplication.primaryScreen().geometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
        self.move(
            int((screen.width() - self.width()) / 2),
            int((screen.height() - self.height()) / 2)
        )

        # self.showFullScreen()

        self.interview_session = {}

        self.new_session_button = QPushButton("🆕 Create New Interview Session")
        self.new_session_button.clicked.connect(self.create_session_form)
        self.load_session_button = QPushButton("📂 Load Interview Session")
        self.load_session_button.clicked.connect(self.load_session)

        self.layout.addWidget(self.new_session_button)
        self.layout.addWidget(self.load_session_button)

        self.DEFAULT_AVATARS = [
            {
                "name": "Rupak",
                "description": "Strategic architect with deep Python insights and real-world debugging wisdom.",
                "voice_style": "calm and analytical",
                "image_url": "/avatars/rupak.jpg"
            },
            {
                "name": "Musk",
                "description": "Visionary leader with a motivational tone and structured delivery.",
                "voice_style": "inspirational and assertive",
                "image_url": "/avatars/musk.webp"
            },
            {
                "name": "Trump",
                "description": "Bold communicator with a direct, high-energy style.",
                "voice_style": "confident and persuasive",
                "image_url": "/avatars/trump.webp"
            },
            {
                "name": "Bachchan",
                "description": "Bold communicator with a direct, high-energy style.",
                "voice_style": "confident and persuasive",
                "image_url": "/avatars/bachchan.webp"
            }
        ]

        self.tts = load_model()

    def create_session_form(self):
        self.form_layout = QFormLayout()

        self.interview_id = str(uuid.uuid4())

        self.interview_name_input = QLineEdit()
        self.interview_name_input.setToolTip("Name of the interview session (e.g., Go Lang Interview)")
        self.role_input = QLineEdit()
        self.role_input.setToolTip("Role being interviewed for (e.g., Senior Go Lang Developer)")
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setToolTip("Date of the interview (stored in UTC format)")
        self.session_timeout_input = QLineEdit()
        self.session_timeout_input.setToolTip("Session Timeout")

        self.evaluation_query_input = QTextEdit()
        
        self.add_question_button = QPushButton("➕ Add Question")
        
        self.add_question_button.clicked.connect(self.open_question_dialog)

        self.save_session_button = QPushButton("💾 Save Session")
        self.save_session_button.clicked.connect(self.save_session)

        self.form_layout.addRow("Interview Name:", self.interview_name_input)
        self.form_layout.addRow("Role:", self.role_input)
        self.form_layout.addRow("Date of Interview:", self.date_input)
        self.form_layout.addRow("Session Timeout:", self.session_timeout_input)
        self.form_layout.addRow("Evaluation Query:", self.evaluation_query_input)
        self.form_layout.addRow(self.add_question_button)
        self.form_layout.addRow(self.save_session_button)

        self.layout.addLayout(self.form_layout)

        self.question_display = QVBoxLayout()
        self.question_group = QGroupBox("📋 Questions")
        self.question_group.setLayout(self.question_display)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.question_group)
        self.layout.addWidget(scroll)
        self.interview_session = {
            "id": self.interview_id,
            "test_name": "",
            "role": "",
            "date": "",
            "session_timeout": 60,
            "evaluation_query": "",
            "avatars": self.DEFAULT_AVATARS,
            "questions": []
        }

    def edit_question_dialog(self, index=None):
        question_data = None
        if index is not None and 0 <= index < len(self.interview_session["questions"]):
            
            question_data = self.interview_session["questions"][index]
        else:
            self.logger.info("question set to none")
            question_data = None
        dialog = QuestionDialog(self, question_data, index)
        dialog.exec()

    def open_question_dialog(self, index=None):
        # Determine the new total number of questions (including the one being added)
        total_questions = len(self.interview_session["questions"]) + 1
        equal_weight = 1 / total_questions

        # Update weights of existing questions
        for q in self.interview_session["questions"]:
            q["weight"] = equal_weight

        # Compute next order
        existing_orders = [q["order"] for q in self.interview_session["questions"]]
        next_order = max(existing_orders) + 1 if existing_orders else 0

        # Prepare new question data
        question_data = {
            "question": "",
            "answer": "",
            "timeout": 20,
            "order": next_order,
            "weight": equal_weight
        }

        # Launch dialog
        dialog = QuestionDialog(self, question_data, total_questions - 1)
        dialog.exec()


    def refresh_question_list(self):
        for i in reversed(range(self.question_display.count())):
            self.question_display.itemAt(i).widget().deleteLater()

        indexed_questions = list(enumerate(self.interview_session["questions"]))
        sorted_questions = sorted(indexed_questions, key=lambda pair: pair[1].get("order", 0))

        for _, (original_index, q) in enumerate(sorted_questions):
            box = QHBoxLayout()
            label = QLabel(f"{q['order']}. {q['question'][:80]}...")
            edit_btn = QPushButton("✏️ Edit")
            edit_btn.clicked.connect(partial(self.edit_question_dialog, original_index))
            box.addWidget(label)
            box.addWidget(edit_btn)
            container = QWidget()
            container.setLayout(box)
            self.question_display.addWidget(container)


    def save_session(self):
        name = self.interview_name_input.text().strip()
        role = self.role_input.text().strip()
        session_timeout_input = self.session_timeout_input.text().strip()
        evaluation_query = self.evaluation_query_input.toPlainText().strip()
        encoded_query = base64.b64encode(evaluation_query.encode("utf-8")).decode("utf-8")

        if not name or not role:
            QMessageBox.warning(self, "Validation Error", "Interview Name and Role are required.")
            return

        self.interview_session["test_name"] = name
        self.interview_session["role"] = role
        date = self.date_input.date().toPyDate()
        self.interview_session["date"] = datetime.combine(date, datetime.min.time()).isoformat() + "Z"
        self.interview_session["session_timeout"] = session_timeout_input
        self.interview_session["evaluation_query"] = encoded_query

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        
        filename = f"{SESSIONS_DIR}/{name.replace(' ', '_')}/{name.replace(' ', '_')}_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(self.interview_session, f, indent=4)

        QMessageBox.information(self, "Session Saved", f"Session saved to {filename}")

    def load_session(self):
        self.create_session_form()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Interview Session", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, "r") as f:
                self.interview_session = json.load(f)

            self.interview_name_input.setText(self.interview_session.get("test_name", ""))
            self.session_timeout_input.setText(self.interview_session.get("role", ""))
            self.role_input.setText(self.interview_session.get("session_timeout", ""))
            equery = self.interview_session.get("evaluation_query")
            equery = base64.b64decode(equery)
            equery = equery.decode("utf-8")
            self.evaluation_query_input.setPlainText(equery)
            date_str = self.interview_session.get("date", "")
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace("Z", "")).date()
                    self.date_input.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
                except Exception as e:
                    self.logger.error(f"Date parsing error: {e}")

            self.refresh_question_list()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InterviewApp()
    window.show()
    sys.exit(app.exec())
