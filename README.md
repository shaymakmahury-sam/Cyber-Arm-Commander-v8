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
