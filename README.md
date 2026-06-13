# Cyber-Arm-Commander-v8
Real-time 3D workspace and control interface for robotic arms.
# 🦾 Cyber-Arm Commander V8

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Cyber-Arm Commander is a premium, real-time 3D workspace and control interface for robotic arms. Built with Python and PyQt5, it seamlessly bridges hardware execution with fluid, decoupled 3D viewport rendering.

## ✨ Features

* **Real-Time 3D Digital Twin:** View your robotic arm in a fully decoupled 30 FPS 3D environment (powered by `pyqtgraph.opengl`).
* **Asynchronous Hardware Pipeline:** Thread-safe background execution ensures your UI never freezes while sending serial commands to the Arduino/Hardware.
* **Voice Command Integration:** Hands-free control using natural speech recognition (e.g., "Open", "Close", "Center").
* **Memory Core:** Record specific servo positions and loop them seamlessly.
* **Dynamic Vitals Monitoring:** Real-time UI tracking for system health, power load, and simulated neural-link handshakes.
* **Customizable UI:** Toggle between Dark/Light themes and Realistic/Wireframe 3D rendering modes.

## 🛠️ Prerequisites

To run this application, you will need Python 3.8+ and the following libraries installed:

```bash
pip install PyQt5 pyqtgraph pyserial SpeechRecognition numpy
(Note: SpeechRecognition also requires PyAudio to access your microphone).

🚀 Getting Started
Clone or download this repository to your local machine.

Ensure your robotic arm (Arduino or compatible microcontroller) is connected via USB.

Run the main script:

Bash
python main.py
Select your COM port from the dropdown menu and click Establish Neural Link.

Use the sliders, voice commands, or memory core to control your hardware!

🔌 Hardware Communication (Serial)
The software sends simple string commands over serial at 128000 baud rate.
The format is S[Joint_Index]:[Angle]\n.

Base: S0:90

Shoulder: S1:90

Elbow: S2:90

Gripper: S3:90

You can easily parse this on your Arduino using Serial.readStringUntil('\n').

📜 License
This project is licensed under the MIT License - see the LICENSE file for details.

👨‍💻 Author
Shaymak Mahury Created for the open-source robotics community.
