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

class QuestionDialog(QDialog):
    def __init__(self, parent, question_data=None, index=None):
        super().__init__(parent)
        self.setWindowTitle("Question Page")
        self.index = index

        print(f"index to dialog = {question_data}, index = {index}")

        screen = QGuiApplication.primaryScreen().geometry()
        self.resize(screen.width() // 2, screen.height() // 2)

        layout = QFormLayout()

        self.question_text = QTextEdit()
        self.question_text.setToolTip("Technical question to ask (e.g., how to implement a worker pool in Go)")
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 9999)
        self.timeout_input.setToolTip("Time in seconds to wait for an answer (e.g., 30, 90)")
        self.order_input = QSpinBox()
        self.order_input.setRange(0, 999)
        self.order_input.setToolTip("Sequence number of the question (e.g., 0, 1, 2)")

        if question_data:
            self.question_text.setPlainText(question_data["question"])
            self.timeout_input.setValue(question_data["timeout"])
            self.order_input.setValue(question_data["order"])

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_question)

        layout.addRow("Question:", self.question_text)
        layout.addRow("Timeout (seconds):", self.timeout_input)
        layout.addRow("Order:", self.order_input)
        layout.addRow(self.save_button)

        self.setLayout(layout)

    def save_question(self):
        question = self.question_text.toPlainText().strip()
        timeout = self.timeout_input.value()
        order = self.order_input.value()

        if not question:
            QMessageBox.warning(self, "Validation Error", "Question cannot be empty.")
            return

        # Check for duplicate order
        for i, q in enumerate(self.parent().interview_session["questions"]):
            if q["order"] == order and i != self.index:
                QMessageBox.warning(self, "Validation Error", f"Order {order} already exists.")
                return

        question_data = {
            "question": question,
            "timeout": timeout,
            "order": order
        }
        self.index = order
        if self.index is not None and 0 <= self.index < len(self.parent().interview_session["questions"]):
            self.parent().interview_session["questions"][self.index] = question_data
        else:
            self.parent().interview_session["questions"].append(question_data)

        print(self.parent().interview_session["questions"])

        self.parent().refresh_question_list()
        self.accept()
        self.index = self.index + 1



class InterviewApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interview Session Manager")
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

    def create_session_form(self):
        self.form_layout = QFormLayout()

        self.interview_name_input = QLineEdit()
        self.interview_name_input.setToolTip("Name of the interview session (e.g., Go Lang Interview)")
        self.role_input = QLineEdit()
        self.role_input.setToolTip("Role being interviewed for (e.g., Senior Go Lang Developer)")
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setToolTip("Date of the interview (stored in UTC format)")

        self.add_question_button = QPushButton("➕ Add Question")
        

        self.add_question_button.clicked.connect(self.open_question_dialog)

        self.save_session_button = QPushButton("💾 Save Session")
        self.save_session_button.clicked.connect(self.save_session)

        self.form_layout.addRow("Interview Name:", self.interview_name_input)
        self.form_layout.addRow("Role:", self.role_input)
        self.form_layout.addRow("Date of Interview:", self.date_input)
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
            "interview_name": "",
            "role": "",
            "date": "",
            "questions": []
        }

        

    def edit_question_dialog(self, index=None):
        question_data = None
        if index is not None and 0 <= index < len(self.interview_session["questions"]):
            print(question_data, index)
            question_data = self.interview_session["questions"][index]
        else:
            print("question set to none")
            question_data = None
        dialog = QuestionDialog(self, question_data, index)
        dialog.exec()

    def open_question_dialog(self, index=None):
        question_data = None
        index = len(self.interview_session["questions"])
        if index == 0:
            question_data = {
                "question": "",
                "timeout": 30,
                "order": 0
            }
        else:
            # Compute next available order
            existing_orders = [q["order"] for q in self.interview_session["questions"]]
            next_order = max(existing_orders) + 1 if existing_orders else 0
            question_data = {
                "question": "",
                "timeout": 30,
                "order": next_order
            }

        dialog = QuestionDialog(self, question_data, index)
        dialog.exec()



    def refresh_question_list(self):
        for i in reversed(range(self.question_display.count())):
            self.question_display.itemAt(i).widget().deleteLater()

        indexed_questions = list(enumerate(self.interview_session["questions"]))
        sorted_questions = sorted(indexed_questions, key=lambda pair: pair[1].get("order", 0))

        for _, (original_index, q) in enumerate(sorted_questions):
            print(q)
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

        if not name or not role:
            QMessageBox.warning(self, "Validation Error", "Interview Name and Role are required.")
            return

        self.interview_session["interview_name"] = name
        self.interview_session["role"] = role
        date = self.date_input.date().toPyDate()
        self.interview_session["date"] = datetime.combine(date, datetime.min.time()).isoformat() + "Z"

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"sessions/{name.replace(' ', '_')}_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(self.interview_session, f, indent=4)

        QMessageBox.information(self, "Session Saved", f"Session saved to {filename}")

    def load_session(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Interview Session", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, "r") as f:
                self.interview_session = json.load(f)

            self.interview_name_input.setText(self.interview_session.get("Interview_Name", ""))
            self.role_input.setText(self.interview_session.get("Role", ""))
            date_str = self.interview_session.get("Date", "")
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace("Z", "")).date()
                    self.date_input.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
                except Exception as e:
                    print(f"Date parsing error: {e}")

            self.refresh_question_list()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InterviewApp()
    window.show()
    sys.exit(app.exec())
