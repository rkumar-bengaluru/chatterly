
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

from chatterly.poc.xttsv2.gen_voice import load_model, gen_voice
from chatterly.utils.constants import SESSIONS_DIR
import uuid
import sounddevice as sd
from scipy.io import wavfile
import os 

from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR

class QuestionDialog(QDialog):
    def __init__(self, parent, question_data=None, index=None):
        super().__init__(parent)
        self.setWindowTitle("Question Page")
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        self.index = index
        self.wav_file = question_data.get("wav_file") if question_data else None

        screen = QGuiApplication.primaryScreen().geometry()
        self.resize(screen.width() // 2, screen.height() // 2)

        layout = QFormLayout()

        self.question_id = str(uuid.uuid4())
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

        # Buttons
        self.generate_audio_button = QPushButton("Generate Audio")
        self.generate_audio_button.clicked.connect(self.generate_audio)

        self.play_audio_button = QPushButton("Play Audio")
        self.play_audio_button.clicked.connect(self.play_audio)
        self.play_audio_button.setEnabled(bool(self.wav_file))

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_question)

        # Layout
        layout.addRow("Question:", self.question_text)
        layout.addRow("Timeout (seconds):", self.timeout_input)
        layout.addRow("Order:", self.order_input)

        button_row = QHBoxLayout()
        button_row.addWidget(self.generate_audio_button)
        button_row.addWidget(self.play_audio_button)
        button_row.addWidget(self.save_button)
        layout.addRow(button_row)

        self.setLayout(layout)

    def generate_audio(self):
        # Dummy logic — replace with actual audio generation later
        self.i_name = self.parent().interview_name_input.text().strip()
        self.parent().current_session = SESSIONS_DIR.joinpath(self.i_name.replace(' ', '_'))
        self.logger.info(f"session_name {self.i_name}, session_dir = {self.parent().current_session}")
        os.makedirs(self.parent().current_session, exist_ok=True)
        self.logger.info(f"current session dir {self.parent().current_session}")


        path = f"{self.parent().current_session}/audio_{self.question_id[-6:]}.wav"
        output_path = gen_voice(self.parent().tts, text=self.question_text.toPlainText().strip(),
                  reference_audio_path="./recording_1760540826.wav",
                  output_path=path,
                  language="en")
        self.wav_file = output_path
        QMessageBox.information(self, "Audio Generated", f"Audio file created: {self.wav_file}")
        self.play_audio_button.setEnabled(True)

    def play_audio(self):
        # Dummy logic — replace with actual playback later
        self.logger.info("🔊 Playing question audio...")
        
        # Read WAV file
        sample_rate, data = wavfile.read(self.wav_file)
        # Play audio
        sd.play(data, samplerate=sample_rate)
        sd.wait()  # Wait until playback is finished
        QMessageBox.information(self, "Play Audio", f"Playing: {self.wav_file}")

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
            "id": self.question_id,
            "question": question,
            "timeout": timeout,
            "order": order,
            "wav_file": self.wav_file
        }

        self.index = order
        if self.index is not None and 0 <= self.index < len(self.parent().interview_session["questions"]):
            self.parent().interview_session["questions"][self.index] = question_data
        else:
            self.parent().interview_session["questions"].append(question_data)

        self.parent().refresh_question_list()
        self.accept()
        self.index += 1