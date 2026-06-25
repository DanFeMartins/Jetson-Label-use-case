import cv2
import numpy as np
import sqlite3
from datetime import datetime

# --- CONFIGURATIONS ---
VIDEO_PATH = '../videos/syntetic.mp4'

ROI_X, ROI_Y, ROI_W, ROI_H = 19, 16, 786, 423
MOTION_THRESHOLD = 1500
STABILIZATION_FRAMES = 15

# --- DATABASE SETUP ---
conn = sqlite3.connect('../database/etiquetas.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS capturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME,
        imagem BLOB
    )
''')
conn.commit()

# --- VIDEO & COOLDOWN SETUP ---
cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
FPS_REAL = int(fps) if fps > 0 else 30 
COOLDOWN_FRAMES = FPS_REAL * 5  
frames_cooldown = 0

fgbg = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=40, detectShadows=False)

estado = 'IDLE'
frames_parado = 0
frames_lidos = 0 
TEMPO_AQUECIMENTO = 30 

print("Monitoring started... Press 'q' to exit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("End of video or error reading frame.")
        break
        
    frames_lidos += 1 
    roi = frame[ROI_Y : ROI_Y + ROI_H, ROI_X : ROI_X + ROI_W]

    # Motion detection processing
    fgmask = fgbg.apply(roi)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
    movimento = cv2.countNonZero(fgmask)

    if frames_lidos > TEMPO_AQUECIMENTO:
        # State Machine
        if estado == 'IDLE':
            if movimento > MOTION_THRESHOLD:
                estado = 'PRINTING'
                print("Status: Printing detected!")
                
        elif estado == 'PRINTING':
            if movimento < MOTION_THRESHOLD:
                estado = 'STABILIZING'
                print(f"Status: Stabilizing... ({frames_parado}/{STABILIZATION_FRAMES})")
                frames_parado = 0
                
        elif estado == 'STABILIZING':
            if movimento > MOTION_THRESHOLD:
                estado = 'PRINTING' 
            else:
                frames_parado += 1
                if frames_parado >= STABILIZATION_FRAMES:
                    # Save frame to SQLite
                    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    _, buffer = cv2.imencode('.jpg', roi)
                    imagem_blob = buffer.tobytes()
                    
                    cursor.execute("INSERT INTO capturas (timestamp, imagem) VALUES (?, ?)", (agora, imagem_blob))
                    conn.commit()
                    print(f"[{agora}] ROI saved to SQLite successfully!")
                    
                    estado = 'COOLDOWN'
                    frames_cooldown = 0
                    
        elif estado == 'COOLDOWN':
            frames_cooldown += 1
            if frames_cooldown >= COOLDOWN_FRAMES:
                estado = 'IDLE'
                print("Status: Cooldown finished. Ready for next label.")
    else:
        cv2.putText(frame, f"WARMING UP... {frames_lidos}/{TEMPO_AQUECIMENTO}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # --- UI RENDERING ---
    if estado == 'COOLDOWN' and frames_cooldown < (COOLDOWN_FRAMES / 2):
        cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0, 255, 0), 10)

    cv2.rectangle(frame, (ROI_X, ROI_Y), (ROI_X + ROI_W, ROI_Y + ROI_H), (0, 0, 255), 2)
    cv2.putText(frame, "ROI", (ROI_X, ROI_Y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    cv2.putText(frame, f"State: {estado}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if estado != 'COOLDOWN' else (255, 165, 0), 2)
    cv2.putText(frame, f"ROI Motion: {movimento}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    if estado == 'COOLDOWN':
        cv2.putText(frame, f"Cooldown: {COOLDOWN_FRAMES - frames_cooldown}f remaining", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)

    cv2.imshow('Camera', frame)
    cv2.imshow('ROI - Motion Mask', fgmask)

    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
conn.close()