#  This is the Python Script for the Robotic Arm Commander

import sys
import serial
import serial.tools.list_ports
import time
import threading
import random
import speech_recognition as sr
import numpy as np
import queue  # Thread-safe worker pipeline

# Core PyQt5 Modules
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSlider, QPushButton, QComboBox, 
                             QFrame, QSplashScreen, QProgressBar, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QThread, QSize, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap, QPainter, QPen

import pyqtgraph.opengl as gl

# --- CONFIGURATION ---
BAUD_RATE = 128000

class ArduinoWorker(QThread):
    def __init__(self, port):
        super().__init__()
        self.port = port
        self.arduino = None
        self.active = False
        self.cmd_queue = queue.Queue()  # Offloads I/O actions from GUI thread

    def run(self):
        try:
            self.arduino = serial.Serial(self.port, BAUD_RATE, timeout=0.1)
            self.active = True
            while self.active:
                try:
                    # Non-blocking queue check keeps loop nimble
                    cmd = self.cmd_queue.get(timeout=0.01)
                    self.arduino.write(f"{cmd}\n".encode())
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Serial Write Error: {e}")
                    self.active = False
        except Exception as e:
            print(f"Serial Connection Error: {e}")

    def send(self, cmd):
        # Instantly pushes command to background pipeline without stalling UI
        self.cmd_queue.put(cmd)

class CyberArmApp(QMainWindow):
    audio_level_signal = pyqtSignal(int)
    playback_step_signal = pyqtSignal(int, int) 

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CYBER-ARM COMMANDER V8 - PREMIUM ULTIMATE WORKSPACE")
        self.setMinimumSize(1300, 800) 
        
        self.worker = None
        self.is_dark_mode = True
        self.is_wireframe = False  
        self.pet_mode_active = False 
        self.recorded_sequence = []
        self.rgb_hue = 0
        
        # Real-time System Vitals Metrics
        self.power_load = 5.0
        self.system_health = 100.0
        self.handshake_step = 0
        self.is_animating_link = False
        self.needs_3d_render = False  # Viewport optimization flag

        # Master Widget Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # === LEFT PANEL: FLOATING CONTROLS ===
        self.left_panel = QFrame()
        self.left_panel.setObjectName("left_panel") 
        self.left_panel.setMinimumWidth(340)
        self.left_panel.setMaximumWidth(380) 
        self.left_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.layout = QVBoxLayout(self.left_panel)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # === RIGHT PANEL: MAX SCALE 3D WORKSPACE ===
        self.right_panel = QFrame()
        self.right_panel.setObjectName("right_panel") 
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_layout.addWidget(self.left_panel, stretch=0)
        self.main_layout.addWidget(self.right_panel, stretch=1)

        self.apply_theme()

        # === UI ELEMENTS ===
        header_layout = QHBoxLayout()
        self.title = QLabel("CYBER-ARM REAL-TIME CORE")
        self.title.setStyleSheet("font-size: 14px; letter-spacing: 1px;")
        
        self.btn_theme = QPushButton("🌓")
        self.btn_theme.setFixedWidth(35)
        self.btn_theme.clicked.connect(self.toggle_theme)
        
        self.btn_fullscreen = QPushButton("⛶ F11")
        self.btn_fullscreen.setFixedWidth(65)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        
        header_layout.addWidget(self.title)
        header_layout.addWidget(self.btn_theme)
        header_layout.addWidget(self.btn_fullscreen)
        self.layout.addLayout(header_layout)

        self.port_select = QComboBox()
        self.port_select.addItems([p.device for p in serial.tools.list_ports.comports()])
        self.btn_connect = QPushButton("ESTABLISH NEURAL LINK")
        self.btn_connect.clicked.connect(self.trigger_neural_handshake)
        self.layout.addWidget(self.port_select)
        self.layout.addWidget(self.btn_connect)

        # Dynamic Vitals UI Group
        self.lbl_vitals = QLabel("SYSTEM HEALTH: 100.0% | STANDBY")
        self.layout.addWidget(self.lbl_vitals)
        
        self.perf_bar = QProgressBar()
        self.perf_bar.setValue(5)
        self.perf_bar.setFormat("POWER LOAD: %p%")
        self.perf_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff007f; }")
        self.layout.addWidget(self.perf_bar)

        self.btn_voice = QPushButton("🎤 START VOICE COMMANDS")
        self.btn_voice.setStyleSheet("background-color: #00ffcc; color: #000; font-weight: bold;")
        self.btn_voice.clicked.connect(self.start_voice_thread)
        self.layout.addWidget(self.btn_voice)
        
        self.audio_vis_bar = QProgressBar()
        self.audio_vis_bar.setRange(0, 100)
        self.audio_vis_bar.setFormat("AUDIO INPUT STRENGTH")
        self.audio_vis_bar.setStyleSheet("QProgressBar::chunk { background-color: #00ff7f; }")
        self.layout.addWidget(self.audio_vis_bar)
        self.audio_level_signal.connect(self.audio_vis_bar.setValue)

        xyz_layout = QVBoxLayout()
        self.xyz_label = QLabel("END EFFECTOR: X: 0.00 | Y: 0.00 | Z: 0.00")
        self.xyz_label.setStyleSheet("color: #00ffcc; font-size: 11px; background: #111; padding: 8px; border-radius: 5px;")
        xyz_layout.addWidget(self.xyz_label)
        
        self.btn_view_mode = QPushButton("VIEW MODE: REALISTIC RENDER")
        self.btn_view_mode.setStyleSheet("background-color: #ffaa00; color: #000; font-weight: bold;")
        self.btn_view_mode.clicked.connect(self.toggle_view_mode)
        xyz_layout.addWidget(self.btn_view_mode)
        self.layout.addLayout(xyz_layout)

        self.sliders = []
        self.slider_labels = []
        self.slider_names = ["BASE (YAW)", "SHOULDER (PITCH)", "ELBOW (PITCH)", "GRIPPER (CLAW)"]
        for i, name in enumerate(self.slider_names):
            lbl = QLabel(f"{name}: 90°")
            sld = QSlider(Qt.Horizontal)
            sld.setRange(0, 180)
            sld.setValue(90)
            sld.valueChanged.connect(lambda val, idx=i: self.move_arm(idx, val))
            self.sliders.append(sld)
            self.slider_labels.append(lbl)
            self.layout.addWidget(lbl)
            self.layout.addWidget(sld)

        self.layout.addWidget(QLabel("--- MEMORY CORE ---"))
        m_layout = QHBoxLayout()
        self.btn_rec = QPushButton("RECORD")
        self.btn_rec.clicked.connect(self.record_current_pos)
        self.btn_play = QPushButton("PLAY LOOP")
        self.btn_play.clicked.connect(self.play_recorded_sequence)
        m_layout.addWidget(self.btn_rec)
        m_layout.addWidget(self.btn_play)
        self.layout.addLayout(m_layout)

        self.btn_sweep = QPushButton("PET MODE: STANDBY")
        self.btn_sweep.clicked.connect(self.toggle_pet_mode)
        self.layout.addWidget(self.btn_sweep)
        self.layout.addStretch()

        # === 3D VIEWPORT ENGINE ===
        self.view = gl.GLViewWidget()
        self.view.setCameraPosition(distance=25, elevation=22, azimuth=45)
        self.right_layout.addWidget(self.view)
        
        self.grid = gl.GLGridItem()
        self.grid.setSize(60, 60)
        self.grid.setSpacing(1, 1)
        self.view.addItem(self.grid)
        
        axis_x = gl.GLLinePlotItem(pos=np.array([[0,0,0], [6,0,0]]), color=[1,0,0,0.5], width=2)
        axis_y = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,6,0]]), color=[0,1,0,0.5], width=2)
        axis_z = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,6]]), color=[0,0,1,0,0.5], width=2)
        self.view.addItem(axis_x); self.view.addItem(axis_y); self.view.addItem(axis_z)

        self.arm_mesh_items = []
        
        self.playback_step_signal.connect(self.handle_background_joint_update)

        # UI Vitals Timer (Handles interface tracking analytics)
        self.vitals_timer = QTimer()
        self.vitals_timer.timeout.connect(self.update_system_loops)
        self.vitals_timer.start(60)

        # Decoupled 30 FPS Graphics Engine Render Loop
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.process_render_heartbeat)
        self.render_timer.start(33) # 33ms roughly maps to a smooth 30 FPS cap

        self.handshake_timer = QTimer()
        self.handshake_timer.timeout.connect(self.execute_handshake_frames)

        self.update_3d_visualizer()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.btn_fullscreen.setText("⛶ F11")
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("⚡ ESC")

    def toggle_view_mode(self):
        self.is_wireframe = not self.is_wireframe
        mode_text = "WIREFRAME SKELETON" if self.is_wireframe else "REALISTIC RENDER"
        self.btn_view_mode.setText(f"VIEW MODE: {mode_text}")
        self.needs_3d_render = True

    def apply_theme(self):
        if self.is_dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #050507; }
                QFrame#left_panel { background-color: rgba(15, 15, 20, 225); border-radius: 8px; }
                QFrame#right_panel { background-color: transparent; border-radius: 8px; }
                QLabel { color: #00ffcc; font-family: 'Consolas'; font-weight: bold; background: transparent; }
                QPushButton { background-color: #101014; border: 1px solid #00ffcc; color: #00ffcc; border-radius: 4px; padding: 8px; }
                QPushButton:hover { background-color: #00ffcc; color: #000; font-weight: bold; }
                QComboBox { background-color: #101014; color: #00ffcc; border: 1px solid #333; padding: 4px; }
                QSlider::handle:horizontal { background: #ff007f; width: 16px; border-radius: 8px; }
                QProgressBar { border: 1px solid #222; background: #08080a; text-align: center; color: white; height: 14px; font-size: 10px; font-weight: bold;}
            """)
            try: self.view.setBackgroundColor('#070709'); self.grid.setColor((0, 255, 204, 30))
            except: pass
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #e2e2e6; }
                QFrame#left_panel { background-color: rgba(255, 255, 255, 225); border-radius: 8px; }
                QFrame#right_panel { background-color: transparent; border-radius: 8px; }
                QLabel { color: #121214; font-family: 'Consolas'; font-weight: bold; background: transparent; }
                QPushButton { background-color: #f0f0f2; border: 1px solid #0078d7; color: #0078d7; border-radius: 4px; padding: 8px; }
                QPushButton:hover { background-color: #0078d7; color: #fff; font-weight: bold; }
                QComboBox { background-color: #f0f0f2; color: #121214; border: 1px solid #ccc; padding: 4px; }
                QSlider::handle:horizontal { background: #0078d7; width: 16px; border-radius: 8px; }
                QProgressBar { border: 1px solid #ccc; background: #e2e2e6; text-align: center; color: black; height: 14px; font-size: 10px; font-weight: bold;}
            """)
            try: self.view.setBackgroundColor('#f0f0f2'); self.grid.setColor((0, 120, 215, 30))
            except: pass

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        self.needs_3d_render = True

    def trigger_neural_handshake(self):
        if self.is_animating_link: return
        self.is_animating_link = True
        self.handshake_step = 0
        self.btn_connect.setEnabled(False)
        self.handshake_timer.start(40)

    def execute_handshake_frames(self):
        self.handshake_step += 1
        if self.handshake_step < 15:
            self.power_load = min(98.0, self.power_load + 6.5)
            self.system_health = max(85.0, self.system_health - 0.8)
            self.btn_connect.setText(f"SYNAPSE SYNC: {self.handshake_step * 6}%")
            self.lbl_vitals.setText(f"HEALTH: {self.system_health:.1f}% | RESOLVING CORES...")
        elif self.handshake_step < 35:
            self.power_load = max(45.0, self.power_load - 2.5) + random.uniform(-4, 4)
            self.system_health = min(99.5, self.system_health + 0.5)
            self.btn_connect.setText("⚡ TUNNELING DOWNLINK...")
            self.lbl_vitals.setText(f"HEALTH: {self.system_health:.1f}% | PIPELINE STABILIZED")
        elif self.handshake_step < 50:
            self.power_load = min(85.0, self.power_load + 1.2)
            self.btn_connect.setText("🔒 SECURING NEURAL GATEWAY...")
        else:
            self.handshake_timer.stop()
            self.is_animating_link = False
            self.btn_connect.setEnabled(True)
            self.system_health = 100.0
            self.connect_serial()

    def connect_serial(self):
        port = self.port_select.currentText()
        if port:
            self.worker = ArduinoWorker(port)
            self.worker.start()
            self.btn_connect.setText("🟢 LINK ACTIVE")
            self.lbl_vitals.setText("HEALTH: 100.0% | NEURAL LINK ONLINE")
        else:
            self.btn_connect.setText("⚠️ LINK STANDALONE (NO HW)")
            self.lbl_vitals.setText("HEALTH: 100.0% | VIRTUAL EMULATION MODE")

    def update_system_loops(self):
        self.rgb_hue = (self.rgb_hue + (6 if self.is_animating_link else 2)) % 360
        color = QColor.fromHsv(self.rgb_hue, 255, 255).name()
        bg_panel = "rgba(15, 15, 20, 230)" if self.is_dark_mode else "rgba(255, 255, 255, 230)"
        
        self.left_panel.setStyleSheet(f"QFrame#left_panel {{ border: 2px solid {color}; background-color: {bg_panel}; }}")
        self.right_panel.setStyleSheet(f"QFrame#right_panel {{ border: 2px solid {color}; background-color: transparent; }}")

        if not self.is_animating_link:
            if self.power_load > 6.0:
                self.power_load -= 0.8
            else:
                self.power_load = max(5.0, self.power_load + random.uniform(-0.2, 0.2))
                
            status_text = "NEURAL LINK ONLINE" if self.worker and self.worker.active else "VIRTUAL EMULATION MODE"
            self.lbl_vitals.setText(f"HEALTH: {self.system_health:.1f}% | {status_text}")
            
        self.perf_bar.setValue(int(self.power_load))

    def move_arm(self, idx, val):
        prev_val = self.sliders[idx].value()
        delta = abs(val - prev_val)
        if delta > 0 and not self.is_animating_link:
            self.power_load = min(95.0, self.power_load + (delta * 1.4))

        self.slider_labels[idx].setText(f"{self.slider_names[idx]}: {val}°")
        self.send_cmd(f"S{idx}:{val}")
        self.needs_3d_render = True  # Signal that state changed; render later

    def process_render_heartbeat(self):
        # Keeps viewport decoupled from processing speed spikes
        if self.needs_3d_render:
            self.update_3d_visualizer()
            self.needs_3d_render = False

    def handle_background_joint_update(self, idx, val):
        if 0 <= idx < len(self.sliders):
            self.sliders[idx].blockSignals(True)
            self.sliders[idx].setValue(val)
            self.sliders[idx].blockSignals(False)
            self.slider_labels[idx].setText(f"{self.slider_names[idx]}: {val}°")
            self.needs_3d_render = True

    def start_voice_thread(self):
        self.btn_voice.setText("🎤 CALIBRATING MIC...")
        threading.Thread(target=self.listen_voice, daemon=True).start()

    def listen_voice(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                r.adjust_for_ambient_noise(source, duration=1.0)
                self.btn_voice.setText("🎤 LISTENING NOW...")
                
                def audio_callback(recognizer, audio_data):
                    try:
                        raw_data = np.frombuffer(audio_data.frame_data, dtype=np.int16)
                        if len(raw_data) > 0:
                            rms = np.sqrt(np.mean(raw_data**2))
                            level = min(100, int(rms / 15))
                            self.audio_level_signal.emit(level)
                    except: pass

                stop_listening = r.listen_in_background(source, audio_callback, phrase_time_limit=4)
                audio = r.listen(source, timeout=7, phrase_time_limit=4)
                stop_listening(wait_for_stop=False)
                
                cmd = r.recognize_google(audio).upper()
                if "OPEN" in cmd: self.playback_step_signal.emit(3, 40); self.send_cmd("S3:40")
                elif "CLOSE" in cmd: self.playback_step_signal.emit(3, 160); self.send_cmd("S3:160")
                elif "CENTER" in cmd: 
                    for i in range(4): self.playback_step_signal.emit(i, 90); self.send_cmd(f"S{i}:90")
            except: pass
                
        self.audio_level_signal.emit(0)
        self.btn_voice.setText("🎤 START VOICE COMMANDS")

    def create_cylinder(self, p1, p2, radius, color):
        v = np.array(p2) - np.array(p1)
        length = np.linalg.norm(v)
        if length < 0.001: return None
        v_dir = v / length
        z_dir = np.array([0, 0, 1])

        cross = np.cross(z_dir, v_dir)
        dot = np.clip(np.dot(z_dir, v_dir), -1.0, 1.0)
        angle = np.degrees(np.arccos(dot))

        md = gl.MeshData.cylinder(rows=20, cols=25, radius=[radius, radius], length=length)
        mesh = gl.GLMeshItem(meshdata=md, smooth=True, color=color, shader='shaded', glOptions='opaque')

        if self.is_wireframe:
            mesh.opts['drawFaces'] = False; mesh.opts['drawEdges'] = True; mesh.opts['edgeColor'] = color

        if np.linalg.norm(cross) > 1e-6: mesh.rotate(angle, cross[0], cross[1], cross[2])
        elif dot < 0: mesh.rotate(180, 1, 0, 0)

        mesh.translate(p1[0], p1[1], p1[2])
        return mesh

    def create_realistic_servo(self, pos, color_body, color_horn, roll=0, pitch=0, yaw=0):
        servo_group = []
        
        def make_cube_mesh(sx, sy, sz):
            verts = np.array([
                [0, 0, 0], [sx, 0, 0], [sx, sy, 0], [0, sy, 0],
                [0, 0, sz], [sx, 0, sz], [sx, sy, sz], [0, sy, sz]
            ], dtype=float)
            faces = np.array([
                [0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7],
                [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]
            ], dtype=int)
            return gl.MeshData(vertexes=verts, faces=faces)
        
        size_x, size_y, size_z = 1.8, 1.0, 1.3
        md_box = make_cube_mesh(size_x, size_y, size_z)
        mesh_box = gl.GLMeshItem(meshdata=md_box, smooth=True, color=color_body, shader='shaded', glOptions='opaque')
        mesh_box.translate(-size_x/2, -size_y/2, -size_z/2)
        servo_group.append(mesh_box)
        
        md_tab = make_cube_mesh(2.6, 0.9, 0.15)
        mesh_tab = gl.GLMeshItem(meshdata=md_tab, smooth=True, color=color_body, shader='shaded', glOptions='opaque')
        mesh_tab.translate(-1.3, -0.45, 0.2)
        servo_group.append(mesh_tab)
        
        md_horn = gl.MeshData.cylinder(rows=12, cols=16, radius=[0.45, 0.45], length=0.4)
        mesh_horn = gl.GLMeshItem(meshdata=md_horn, smooth=True, color=color_horn, shader='shaded', glOptions='opaque')
        mesh_horn.translate(0.4, 0, size_z/2)
        servo_group.append(mesh_horn)

        if self.is_wireframe:
            for item in servo_group:
                item.opts['drawFaces'] = False
                item.opts['drawEdges'] = True
                item.opts['edgeColor'] = color_body

        for item in servo_group:
            if roll != 0: item.rotate(roll, 1, 0, 0)
            if pitch != 0: item.rotate(pitch, 0, 1, 0)
            if yaw != 0: item.rotate(yaw, 0, 0, 1)
            item.translate(pos[0], pos[1], pos[2])
            self.view.addItem(item)
            self.arm_mesh_items.append(item)

    def update_3d_visualizer(self):
        for item in self.arm_mesh_items: self.view.removeItem(item)
        self.arm_mesh_items.clear()

        t_yaw = np.radians(self.sliders[0].value() - 90)
        t_shoulder = np.radians(90 - self.sliders[1].value()) 
        t_elbow = np.radians(90 - self.sliders[2].value())    
        val_gripper = self.sliders[3].value()
        
        L_base, L_bicep, L_forearm, L_wrist = 3.5, 6.5, 5.5, 1.8

        x1, y1, z1 = 0, 0, L_base
        dx1 = L_bicep * np.sin(t_shoulder) * np.cos(t_yaw)
        dy1 = L_bicep * np.sin(t_shoulder) * np.sin(t_yaw)
        dz1 = L_bicep * np.cos(t_shoulder)
        x2, y2, z2 = x1 + dx1, y1 + dy1, z1 + dz1
        
        dx2 = L_forearm * np.sin(t_shoulder + t_elbow) * np.cos(t_yaw)
        dy2 = L_forearm * np.sin(t_shoulder + t_elbow) * np.sin(t_yaw)
        dz2 = L_forearm * np.cos(t_shoulder + t_elbow)
        x3, y3, z3 = x2 + dx2, y2 + dy2, z2 + dz2
        
        dx3 = L_wrist * np.sin(t_shoulder + t_elbow) * np.cos(t_yaw)
        dy3 = L_wrist * np.sin(t_shoulder + t_elbow) * np.sin(t_yaw)
        dz3 = L_wrist * np.cos(t_shoulder + t_elbow)
        x4, y4, z4 = x3 + dx3, y3 + dy3, z3 + dz3

        self.xyz_label.setText(f"END EFFECTOR -> X: {x4:5.2f}  |  Y: {y4:5.2f}  |  Z: {z4:5.2f}")

        c_anodized_black = [0.11, 0.11, 0.13, 1.0]
        c_brushed_alloy = [0.68, 0.70, 0.74, 1.0] 
        c_servo_case = [0.15, 0.15, 0.17, 1.0] 
        c_machined_brass = [0.82, 0.64, 0.20, 1.0]  
        c_structural_base = [0.07, 0.07, 0.09, 1.0]

        base_cyl = gl.GLMeshItem(meshdata=gl.MeshData.cylinder(rows=15, cols=25, radius=[3.2, 2.8], length=L_base),
                                 smooth=True, color=c_structural_base, shader='shaded')
        if self.is_wireframe:
            base_cyl.opts['drawFaces'] = False; base_cyl.opts['drawEdges'] = True; base_cyl.opts['edgeColor'] = c_structural_base
        self.view.addItem(base_cyl)
        self.arm_mesh_items.append(base_cyl)

        link1 = self.create_cylinder([x1, y1, z1], [x2, y2, z2], 0.85, c_brushed_alloy)
        link2 = self.create_cylinder([x2, y2, z2], [x3, y3, z3], 0.65, c_brushed_alloy)
        link3 = self.create_cylinder([x3, y3, z3], [x4, y4, z4], 0.45, c_anodized_black)
        for l in filter(None, [link1, link2, link3]):
            self.view.addItem(l)
            self.arm_mesh_items.append(l)

        yaw_deg = np.degrees(t_yaw)
        pitch_deg = np.degrees(t_shoulder)
        self.create_realistic_servo([x1, y1, z1], c_servo_case, c_machined_brass, yaw=yaw_deg)
        self.create_realistic_servo([x2, y2, z2], c_servo_case, c_machined_brass, yaw=yaw_deg, pitch=pitch_deg)
        self.create_realistic_servo([x3, y3, z3], c_servo_case, c_machined_brass, yaw=yaw_deg, pitch=pitch_deg)

        claw_spread = 0.25 + ((val_gripper / 180.0) * 1.6)
        ortho_x = claw_spread * -np.sin(t_yaw)
        ortho_y = claw_spread * np.cos(t_yaw)
        
        left_knuckle = [x4 + ortho_x, y4 + ortho_y, z4]
        right_knuckle = [x4 - ortho_x, y4 - ortho_y, z4]
        
        fwd_x = 1.6 * np.sin(t_shoulder + t_elbow) * np.cos(t_yaw)
        fwd_y = 1.6 * np.sin(t_shoulder + t_elbow) * np.sin(t_yaw)
        fwd_z = 1.6 * np.cos(t_shoulder + t_elbow)
        
        left_tip = [left_knuckle[0] + fwd_x, left_knuckle[1] + fwd_y, left_knuckle[2] + fwd_z]
        right_tip = [right_knuckle[0] + fwd_x, right_knuckle[1] + fwd_y, right_knuckle[2] + fwd_z]

        c1 = self.create_cylinder([x4, y4, z4], left_knuckle, 0.22, c_machined_brass)
        c2 = self.create_cylinder(left_knuckle, left_tip, 0.16, c_machined_brass)
        c3 = self.create_cylinder([x4, y4, z4], right_knuckle, 0.22, c_machined_brass)
        c4 = self.create_cylinder(right_knuckle, right_tip, 0.16, c_machined_brass)
        
        for c in filter(None, [c1, c2, c3, c4]):
            self.view.addItem(c)
            self.arm_mesh_items.append(c)

    def send_cmd(self, cmd):
        if self.worker: self.worker.send(cmd)

    def record_current_pos(self):
        self.recorded_sequence.append([sld.value() for sld in self.sliders])

    def play_recorded_sequence(self):
        def play_thread():
            for angles in self.recorded_sequence:
                for i, ang in enumerate(angles): 
                    self.send_cmd(f"S{i}:{ang}")
                    self.playback_step_signal.emit(i, ang) 
                time.sleep(1.0)
        threading.Thread(target=play_thread, daemon=True).start()

    def toggle_pet_mode(self):
        self.pet_mode_active = not self.pet_mode_active
        self.btn_sweep.setText("PET MODE: ACTIVE" if self.pet_mode_active else "PET MODE: STANDBY")
        if self.pet_mode_active: threading.Thread(target=self.pet_logic, daemon=True).start()

    def pet_logic(self):
        while self.pet_mode_active:
            target_angle = random.randint(60, 120)
            self.send_cmd(f"S0:{target_angle}")
            self.playback_step_signal.emit(0, target_angle)
            time.sleep(0.5)


# --- INITIALIZATION RUNTIME PIPELINE ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    canvas_w, canvas_h = 800, 450
    splash_bg = QPixmap(QSize(canvas_w, canvas_h))
    splash_bg.fill(QColor("#0a0a0c"))
    
    painter = QPainter(splash_bg)
    painter.setRenderHint(QPainter.Antialiasing)
    
    logo_size = 140
    logo_x = (canvas_w - logo_size) // 2
    logo_y = 60
    
    logo_pixmap = QPixmap("arm_icon.png")
    if not logo_pixmap.isNull():
        scaled_logo = logo_pixmap.scaled(logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(logo_x, logo_y, scaled_logo)
    else:
        painter.setPen(QPen(QColor("#00ffcc"), 2, Qt.DashLine))
        painter.drawRect(logo_x, logo_y, logo_size, logo_size)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawText(logo_x, logo_y + (logo_size//2), logo_size, 100, Qt.AlignCenter, "[ LOGO FILE ]")
        
    painter.end()
    
    splash = QSplashScreen(splash_bg, Qt.WindowStaysOnTopHint)
    
    label_title = QLabel("ROBOTIC ARM SYSTEM V8", splash)
    label_title.setStyleSheet("color: #00ffcc; font-family: 'Consolas'; font-size: 26px; font-weight: bold; background: transparent;")
    label_title.setGeometry(0, 240, canvas_w, 40)
    label_title.setAlignment(Qt.AlignCenter)
    
    label_status = QLabel("INITIALIZING COMPONENT MATRIX ENGINE...", splash)
    label_status.setStyleSheet("color: #88888b; font-family: 'Consolas'; font-size: 20px; background: transparent;")
    label_status.setGeometry(0, 290, canvas_w, 30)
    label_status.setAlignment(Qt.AlignCenter)

    label_credit = QLabel("Created by Shaymak Mahury", splash)
    label_credit.setStyleSheet("color: #55555a; font-family: 'Consolas'; font-size: 20px; font-style: normal; background: transparent;")
    label_credit.setGeometry(canvas_w - 330, canvas_h - 50, 290, 30)
    label_credit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    
    splash.show()
    app.processEvents()
    
    main_window = None
    def start_main():
        global main_window
        main_window = CyberArmApp()
        main_window.show()
        splash.finish(main_window)

    QTimer.singleShot(10000, start_main) 
    sys.exit(app.exec_())
