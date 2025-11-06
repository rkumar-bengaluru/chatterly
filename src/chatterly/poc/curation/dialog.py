
import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QDateEdit, QDialog, QLabel, QSpinBox,
    QHBoxLayout, QScrollArea, QGroupBox, QFileDialog, QMessageBox
)
from PyQt6.QtWidgets import QProgressDialog
from PyQt6.QtCore import Qt
import time
import base64
import os
import time 
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
from PyQt6.QtWidgets import QDoubleSpinBox
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
        self.weight_input = QDoubleSpinBox(self)
        self.weight_input.setDecimals(2)         # Optional: show up to 2 decimal places
        self.weight_input.setRange(0.0, 1.0)      # Set appropriate range for weights
        self.weight_input.setToolTip("Weight of the question (between 0-1)")

        # self.weight_input = QSpinBox()
        # self.weight_input.setRange(0, 999)
        # self.weight_input.setToolTip("Weight of the question (between 0-1)")

        if question_data:
            self.question_text.setPlainText(question_data["question"])
            self.timeout_input.setValue(question_data["timeout"])
            self.order_input.setValue(question_data["order"])
            self.weight_input.setValue(question_data["weight"])

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
        layout.addRow("Weight:", self.weight_input)

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

        # Example: Map of avatars with name and reference audio
        # Replace this with your actual data source (e.g., self.avatar_map)
        avatar_map = [
            {"avatar_name": "Rupak", "reference_audio_path": "./recording_rupak.wav"},
            {"avatar_name": "Trump",   "reference_audio_path": "./recording_trump.wav"},
            {"avatar_name": "Musk", "reference_audio_path": "./recording_musk.wav"},
        ]

        total_avatars = len(avatar_map)
        if total_avatars == 0:
            QMessageBox.warning(self, "No Avatars", "No avatar audio references found.")
            return

        # Create progress dialog
        progress = QProgressDialog("Generating audio for avatars...", "Cancel", 0, total_avatars, self)
        progress.setWindowTitle("Audio Generation in Progress")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)  # Show immediately

        generated_files = {}

        try:
            for index, avatar in enumerate(avatar_map):
                if progress.wasCanceled():
                    break

                avatar_name = avatar["avatar_name"]
                ref_audio = avatar["reference_audio_path"]

                progress.setValue(index)
                progress.setLabelText(f"Generating audio for {avatar_name}...")

                # Generate unique output path per avatar
                safe_avatar_name = "".join(c for c in avatar_name if c.isalnum() or c in " _-").rstrip()
                output_dir = f"{self.parent().current_session}/{self.question_id}"
                os.makedirs(output_dir, exist_ok=True)
                output_filename = f"{self.question_id}/{safe_avatar_name}.wav"
                output_path = self.parent().current_session / output_filename

                self.logger.info(f"Generating voice for {avatar_name} -> {output_path}")

                # Call your TTS function (gen_voice)
                generated_path = gen_voice(
                    self.parent().tts,
                    text=self.question_text.toPlainText().strip(),
                    reference_audio_path=ref_audio,
                    output_path=str(output_path),
                    language="en"
                )

                generated_files[avatar_name] = generated_path

                # Small delay to update UI (optional, remove if gen_voice is fast)
                time.sleep(0.1)

            progress.setValue(total_avatars)

            # Store results for later use (e.g., playback per avatar)
            self.generated_audio_files = generated_files  # e.g., {"Alice": "/path/to/audio_..._Alice.wav", ...}

            # Success message with summary
            summary = "\n".join([f"{name}: {os.path.basename(path)}" for name, path in generated_files.items()])
            QMessageBox.information(
                self,
                "Audio Generation Complete",
                f"Generated {len(generated_files)} audio file(s):\n\n{summary}"
            )

            # Enable play button (you may want a dropdown to select avatar later)
            self.play_audio_button.setEnabled(True)

        except Exception as e:
            self.logger.error(f"Error during audio generation: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate audio:\n{str(e)}")
        finally:
            progress.close()


    def generate_audio_01(self):
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
        order   = self.order_input.value()

        if not question:
            QMessageBox.warning(self, "Validation Error", "Question cannot be empty.")
            return

        # ---- duplicate-order check ------------------------------------------------
        for i, q in enumerate(self.parent().interview_session["questions"]):
            if q["order"] == order and i != self.index:
                QMessageBox.warning(self, "Validation Error",
                                    f"Order {order} already exists.")
                return

        # ---- build the avatars array ---------------------------------------------
        avatars = []

        # `self.generated_audio_files` is filled by generate_audio()
        #   →  {"Alice": "/full/path/audio_001_Alice.wav", ...}
        if hasattr(self, "generated_audio_files") and self.generated_audio_files:
            for name, wav_path in self.generated_audio_files.items():
                # 1. absolute path (already absolute in generate_audio)
                abs_path = os.path.abspath(wav_path)

                # 2. read file + base64 encode
                try:
                    with open(abs_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                except Exception as e:
                    self.logger.error(f"Failed to base64-encode {abs_path}: {e}")
                    b64 = ""

                avatars.append({
                    "name": name,
                    "wav_file": abs_path,                 # absolute path
                    "base64_encoded_voice": b64           # ready for JS
                })
        else:
            # ---- fallback for old single-file mode --------------------------------
            # (keeps the session compatible if you open an old interview)
            wav_path = getattr(self, "wav_file", None)
            if wav_path:
                abs_path = os.path.abspath(wav_path)
                try:
                    with open(abs_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                except Exception:
                    b64 = ""
                avatars.append({
                    "name": "default",                     # you can change this
                    "wav_file": abs_path,
                    "base64_encoded_voice": b64
                })

        # ---- final question payload ------------------------------------------------
        question_data = {
            "id": self.question_id,
            "question": question,
            "timeout": timeout,
            "order": order,                             # <-- new structure
            "weight": self.weight_input.value()
        }

        # ---- insert / update in the interview session -----------------------------
        if self.index is not None and 0 <= self.index < len(self.parent().interview_session["questions"]):
            self.parent().interview_session["questions"][self.index] = question_data
        else:
            self.parent().interview_session["questions"].append(question_data)

        # refresh UI & close dialog
        self.parent().refresh_question_list()
        self.accept()

        # (optional) keep a running index for the next “Add” click
        # self.index += 1


    def save_question_01(self):
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