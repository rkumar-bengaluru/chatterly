import cv2
import numpy as np
import time
import threading
import pyaudio
import wave
import subprocess
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QPropertyAnimation

class MockMeetScreen(QWidget):
    def __init__(self, metadata, stacked_widget):
        super().__init__()
        self.metadata = metadata
        self.stacked_widget = stacked_widget
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.audio_active = False
        self.audio_level = 0
        self.session_start_time = None
        self.countdown_seconds = 3
        self.recording = False
        self.video_writer = None
        self.audio_frames = []
        self.audio_stream = None

        self.init_ui()
        self.start_countdown()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"<h2>{self.metadata['interview_name']}</h2>"))
        layout.addWidget(QLabel(f"<i>Role: {self.metadata['role']}</i>"))

        self.countdown_label = QLabel("")
        self.countdown_label.setFont(QFont("Arial", 24))
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_label)

        self.video_label = QLabel("Starting camera...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)

        self.audio_label = QLabel("🎙️ Microphone: Active")
        self.audio_waveform = QLabel("▁▂▃▄▅▆▇█")
        self.audio_waveform.setFont(QFont("Courier", 24))
        layout.addWidget(self.audio_label)
        layout.addWidget(self.audio_waveform)

        self.timer_label = QLabel("⏱️ Session Time: 00:00")
        layout.addWidget(self.timer_label)

        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.start_recording)
        layout.addWidget(self.record_btn)

        btn_layout = QHBoxLayout()
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.close_session)
        btn_layout.addStretch()
        btn_layout.addWidget(self.disconnect_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.update_timer)



    def start_countdown(self):
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)

    def update_countdown(self):
        if self.countdown_seconds > 0:
            self.countdown_label.setText(f"Starting in {self.countdown_seconds}...")
            self.countdown_seconds -= 1
        else:
            self.countdown_label.setText("")
            self.countdown_timer.stop()
            self.session_start_time = time.time()
            self.timer.start(30)
            self.session_timer.start(1000)
            self.start_audio_monitor()

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(pixmap.scaled(480, 360, Qt.AspectRatioMode.KeepAspectRatio))

            if self.recording and self.video_writer:
                self.video_writer.write(frame)

    def update_timer(self):
        elapsed = int(time.time() - self.session_start_time)
        minutes, seconds = divmod(elapsed, 60)
        self.timer_label.setText(f"⏱️ Session Time: {minutes:02}:{seconds:02}")

    def start_audio_monitor(self):
        def monitor():
            p = pyaudio.PyAudio()
            self.audio_stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100,
                                       input=True, frames_per_buffer=1024)
            self.audio_active = True
            while self.audio_active:
                data = self.audio_stream.read(1024, exception_on_overflow=False)
                self.audio_frames.append(data)
                peak = np.abs(np.frombuffer(data, dtype=np.int16)).max()
                waveform = "▁▂▃▄▅▆▇█"[:min(8, peak // 500)]
                self.audio_waveform.setText(waveform or "▁")
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            p.terminate()

        threading.Thread(target=monitor, daemon=True).start()

    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.record_btn.setText("Recording...")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.video_writer = cv2.VideoWriter("interview_video.avi", fourcc, 20.0, (640, 480))
            self.audio_frames = []

    def combine_audio_video(self, video_path, audio_path, output_path):
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite if exists
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-strict", "experimental",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def close_session(self):
        self.timer.stop()
        self.session_timer.stop()
        self.audio_active = False
        if self.cap.isOpened():
            self.cap.release()
        if self.video_writer:
            self.video_writer.release()
        if self.recording:
            wf = wave.open("interview_audio.wav", 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.audio_frames))
            wf.close()
        self.combine_audio_video("./interview_video.avi", "./interview_audio.wav", "interview_combined.mp4")
        self.video_label.setText("Camera disconnected.")
        self.audio_label.setText("🎙️ Microphone: Disconnected")
        self.audio_waveform.setText("")
        self.countdown_label.setText("Session ended.")
