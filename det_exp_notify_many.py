import cv2
import mediapipe as mp
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import atexit
import signal


class StudentActivityMonitor:
    def __init__(self):
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Camera setup
        self.cap = cv2.VideoCapture(0)

        # Initialize activity tracking for each student (using unique IDs)
        self.student_activities = {}

    def calculate_head_orientation(self, landmarks):
        # Nose tip and eye corners
        nose_tip = landmarks[1]
        left_eye = landmarks[33]
        right_eye = landmarks[263]

        # Calculate eye center
        eye_center_x = (left_eye.x + right_eye.x) / 2
        eye_center_y = (left_eye.y + right_eye.y) / 2

        # Calculate pitch and yaw
        pitch = (nose_tip.y - eye_center_y) * self.frame_height
        yaw = (nose_tip.x - eye_center_x) * self.frame_width

        return pitch, yaw

    def classify_activity(self, pitch, yaw):
        if -10 < pitch < 10 and -15 < yaw < 15:
            return "Watching Blackboard"
        elif pitch > 10:
            return "Looking Down (Using Phone/Writing)"
        elif pitch < -10:
            return "Looking Up (Distracted)"
        elif yaw > 15:
            return "Looking Right (Talking/Distraction)"
        elif yaw < -15:
            return "Looking Left (Talking/Distraction)"
        else:
            return "Unknown Activity"

    def detect_activities(self):
        try:
            while self.cap.isOpened():
                success, image = self.cap.read()
                if not success:
                    break

                self.frame_height, self.frame_width = image.shape[:2]
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = self.face_mesh.process(image)

                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                if results.multi_face_landmarks:
                    for i, face_landmarks in enumerate(results.multi_face_landmarks):
                        try:
                            landmarks = face_landmarks.landmark
                            pitch, yaw = self.calculate_head_orientation(landmarks)
                            activity = self.classify_activity(pitch, yaw)

                            # Track activity for each student by their index
                            self.student_activities[f"Student {i + 1}"] = activity

                            # Display student activity
                            cv2.putText(image, f"Student {i + 1}: {activity}", (10, 50 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                            # Draw landmarks
                            self.mp_drawing.draw_landmarks(
                                image, face_landmarks, self.mp_face_mesh.FACEMESH_CONTOURS
                            )
                        except IndexError as e:
                            print(f"Error accessing landmarks: {e}")

                # Display the image
                cv2.imshow('Student Activity Monitor', image)

                # Break loop on 'q' key press
                if cv2.waitKey(5) & 0xFF == ord('q'):
                    break

        finally:
            # Cleanup resources
            self.cap.release()
            cv2.destroyAllWindows()

    def send_email_summary(self, teacher_email):
        # Summarize activities for all students
        summary = "\n".join([f"{student}: {activity}" for student, activity in self.student_activities.items()])

        sender_email = "midbits4@gmail.com"
        sender_password = "otsm bvxw axjz llun"

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = teacher_email
        message["Subject"] = "Classroom Activity Summary"
        body = f"""
        Dear Teacher,

        Here is the summary of student activities during your class:

        {summary}

        Best regards,
        Student Activity Monitor
        """
        message.attach(MIMEText(body, "plain"))

        # Send email
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, teacher_email, message.as_string())
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def run(self, teacher_email):
        try:
            print("Starting activity detection...")
            self.detect_activities()
        except Exception as e:
            print(f"An error occurred during execution: {e}")
        finally:
            print("Sending email summary...")
            self.send_email_summary(teacher_email)
            print("Email sent. Program terminated.")


def signal_handler(sig, frame):
    print("Signal received. Cleaning up and sending email...")
    monitor.send_email_summary("teacher_email@example.com")
    print("Email sent. Exiting program.")
    exit(0)


# Main execution
if __name__ == "__main__":
    teacher_email = "peersyed105@gmail.com"  # Replace with the teacher's email address
    monitor = StudentActivityMonitor()

    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Register atexit to ensure email is sent if program ends normally
    atexit.register(lambda: monitor.send_email_summary(teacher_email))

    monitor.run(teacher_email)
