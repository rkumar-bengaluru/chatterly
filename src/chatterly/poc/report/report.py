
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os 

from chatterly.utils.logger import setup_daily_logger
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR

class InterviewReport:

    def __init__(self, data):
        self.data = data 
        self.host = "smtp.gmail.com"
        self.port = 465
        self.sender = "rupak.kumar.ambasta@gmail.com"
        self.reciepient = data["user_email"]
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)

    def send_email_report(self):
        self.html_content = self.generate_html_report()
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {self.data['interview_name']} for role {self.data['role']} on date {self.data['date']} is Ready"
        msg["From"] = self.sender
        msg["To"] = self.reciepient
        msg.attach(MIMEText(self.html_content, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self.sender, os.getenv("GMAIL_APP_PASS"))  # Auth happens here
            server.sendmail(self.sender, self.reciepient, msg.as_string())
            self.logger.info(f"Email sent to {self.reciepient}")


    def generate_html_report(self):
        interview_data = self.data 
        user = interview_data["user_email"]
        role = interview_data["role"]
        date = interview_data["date"]
        name = interview_data["interview_name"]
        recording = interview_data["recording"]
        overall_score = sum(q["score"] * q["weight"] for q in interview_data["questions"])
        
        video_link = f'<a href="{recording}" target="_blank">Recordings</a>' 
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h2 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
                .score {{ font-weight: bold; color: #27ae60; }}
            </style>
        </head>
        <body>
            <h2>Interview Report: {name}</h2>
            <p><strong>Candidate:</strong> {user}<br>
            <strong>Role:</strong> {role}<br>
            <strong>Date:</strong> {date}<br>
            <strong>Overall Score:</strong> <span class="score">{overall_score:.2f}</span></p>
            <strong>Date:</strong> {date}<br>
            <strong>VideoLink:</strong> {video_link}<br>

            <h3>Question Breakdown</h3>
            <table>
                <tr>
                    <th>Order</th>
                    <th>Question</th>
                    <th>You Response</th>
                    <th>Score</th>
                    <th>Weight</th>
                    <th>Rationale</th>
                </tr>
        """

        for q in interview_data["questions"]:
            html += f"""
                <tr>
                    <td>{q["order"]}</td>
                    <td>{q["question"]}</td>
                    <td>{q["user_answer"]}</td>
                    <td>{q["score"]:.2f}</td>
                    <td>{q["weight"]:.2f}</td>
                    <td>{q["rationale"]}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """
        return html
