import cv2
import numpy as np
import sqlite3
from datetime import datetime

# ================= CONFIGURAÇÕES =================
VIDEO_PATH = '../videos/syntetic.mp4'

ROI_X = 19
ROI_Y = 16
ROI_W = 786
ROI_H = 423
MOTION_THRESHOLD = 1500
STABILIZATION_FRAMES = 15
# =================================================

# ================= BANCO DE DADOS =================
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
# =================================================

cap = cv2.VideoCapture(VIDEO_PATH)

# --- CONFIGURAÇÃO DO FREEZETIME (COOLDOWN) ---
# Descobre o FPS do vídeo para calcular quantos frames equivalem a 1 segundo
fps = cap.get(cv2.CAP_PROP_FPS)
FPS_REAL = int(fps) if fps > 0 else 30 
COOLDOWN_FRAMES = FPS_REAL * 5  # 5 segundo convertido em quantidade de frames
frames_cooldown = 0
# ---------------------------------------------

fgbg = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=40, detectShadows=False)

estado = 'IDLE'
frames_parado = 0
frames_lidos = 0 
TEMPO_AQUECIMENTO = 30 

print("Iniciando monitoramento... Pressione 'q' para sair.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Fim do vídeo ou erro ao ler o frame.")
        break
        
    frames_lidos += 1 

    roi = frame[ROI_Y : ROI_Y + ROI_H, ROI_X : ROI_X + ROI_W]

    fgmask = fgbg.apply(roi)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
    movimento = cv2.countNonZero(fgmask)

    if frames_lidos > TEMPO_AQUECIMENTO:
        
        # MÁQUINA DE ESTADOS ALTERADA
        if estado == 'IDLE':
            if movimento > MOTION_THRESHOLD:
                estado = 'PRINTING'
                print("Status: Impressão detectada!")
                
        elif estado == 'PRINTING':
            if movimento < MOTION_THRESHOLD:
                estado = 'STABILIZING'
                print(f"Status: Estabilizando... ({frames_parado}/{STABILIZATION_FRAMES})")
                frames_parado = 0
                
        elif estado == 'STABILIZING':
            if movimento > MOTION_THRESHOLD:
                estado = 'PRINTING' 
            else:
                frames_parado += 1
                if frames_parado >= STABILIZATION_FRAMES:
                    # === SALVANDO NO SQLITE ===
                    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    _, buffer = cv2.imencode('.jpg', roi)
                    imagem_blob = buffer.tobytes()
                    
                    cursor.execute("INSERT INTO capturas (timestamp, imagem) VALUES (?, ?)", (agora, imagem_blob))
                    conn.commit()
                    
                    print(f"[{agora}] Foto da ROI salva no SQLite com sucesso!")
                    
                    # Em vez de voltar para IDLE, vai para o COOLDOWN
                    estado = 'COOLDOWN'
                    frames_cooldown = 0
                    
        elif estado == 'COOLDOWN':
            frames_cooldown += 1
            if frames_cooldown >= COOLDOWN_FRAMES:
                estado = 'IDLE'
                print("Status: Freezetime encerrado. Pronto para próxima label.")
    else:
        cv2.putText(frame, f"AQUECENDO IA... {frames_lidos}/{TEMPO_AQUECIMENTO}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # --- RENDERIZAÇÃO DA INTERFACE ---
    # Efeito visual: Mantém a borda verde piscando durante metade do tempo de cooldown de forma fluida
    if estado == 'COOLDOWN' and frames_cooldown < (COOLDOWN_FRAMES / 2):
        cv2.rectangle(frame, (0,0), (frame.shape[1], frame.shape[0]), (0, 255, 0), 10)

    cv2.rectangle(frame, (ROI_X, ROI_Y), (ROI_X + ROI_W, ROI_Y + ROI_H), (0, 0, 255), 2)
    cv2.putText(frame, "ROI", (ROI_X, ROI_Y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # Mostra informações textuais na tela
    cv2.putText(frame, f"Estado: {estado}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if estado != 'COOLDOWN' else (255, 165, 0), 2)
    cv2.putText(frame, f"Movimento na ROI: {movimento}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    if estado == 'COOLDOWN':
        # Mostra na tela quantos frames faltam para liberar o sensor de movimento
        cv2.putText(frame, f"Freezetime: {COOLDOWN_FRAMES - frames_cooldown}f restantes", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)

    cv2.imshow('Camera', frame)
    cv2.imshow('ROI - Mascara de Movimento', fgmask)

    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
conn.close()