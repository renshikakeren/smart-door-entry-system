AI-Powered Smart Door Entry System
Project Overview
This is a secure, AI-powered smart door access control system developed with Python and the Flask framework. The system uses computer vision and machine learning to perform real-time facial recognition, providing a robust and intelligent security solution for homes or offices. It features a multi-layered authentication process, proactive email alerts, and a web-based logging dashboard for comprehensive monitoring.

Features
Two-Factor Authentication: The system requires a correct password input before initiating the facial recognition scan, adding an extra layer of security.

Real-time Facial Recognition: Utilizes the DeepFace library to compare a live camera feed with a database of pre-approved faces, granting access only to recognized individuals.

Proactive Email Alerts: Automatically sends an email with a captured image to the owner when an unknown person is detected or after multiple failed password attempts. The email includes actionable links to remotely approve or deny access.

Comprehensive Logging: All access attempts, including person's name, password status, face recognition status, and door status, are logged to an Excel file (tracking_log.xlsx) using the Pandas library.

Web Interface: A user-friendly web interface built with HTML, CSS, and Flask allows for password input and provides a live camera feed for remote monitoring.

Voice Notifications: Provides real-time audio feedback for key events, such as "Welcome, [User's Name]!" or "Access Denied!".

Technologies Used
Python: The core programming language for the application logic.

Flask: A lightweight web framework used to build the web application and API endpoints.

DeepFace: A powerful framework for facial recognition and analysis.

Pandas: Used for data manipulation and logging to Excel.

pyttsx3: A Python library for text-to-speech conversion.

smtplib: For sending email alerts.

HTML/CSS: For the front-end design and user interface.

OpenCV (cv2): For capturing and processing camera images.

Setup and Installation
Follow these steps to get the project up and running on your local machine.

Download the project files:
Download the project files from GitHub and extract them to a folder on your computer.

Install the required libraries:
Open a command prompt or terminal, navigate to the project folder, and run:

pip install -r requirements.txt

(Note: You may need to create a requirements.txt file by running pip freeze > requirements.txt after installing all dependencies.)

Set up email credentials:

In app.py, update SENDER_EMAIL and SENDER_PASSWORD with your own email and an app password (if using Gmail).

OWNER_EMAIL should be the address where you want to receive alerts.

Create your "Allowed_faces" database:

Create a folder named Allowed_faces.

Add images of authorized individuals to this folder. The DeepFace library will use these images as its database.

Update the ALLOWED_FACES_MAPPING dictionary in app.py to map the image filenames to the person's name (e.g., "Allowed_faces/john_doe.jpg": "John Doe").

How to Run
After completing the setup, run the Flask application from your command prompt or terminal:

python app.py

The application will launch and open a browser window to http://127.0.0.1:5000/.

