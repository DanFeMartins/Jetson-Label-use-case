import sqlite3
import cv2
import numpy as np
import easyocr

# --- CONFIGURATIONS ---
DB_PATH = '../database/etiquetas.db'

def processar_ocr_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add 'identificador' column if it does not exist
    try:
        cursor.execute("ALTER TABLE capturas ADD COLUMN identificador TEXT")
        conn.commit()
        print("[INFO] 'identificador' column added to 'capturas' table.")
    except sqlite3.OperationalError:
        print("[INFO] 'identificador' column already exists. Proceeding...")

    print("[INFO] Initializing EasyOCR engine...")
    reader = easyocr.Reader(['pt', 'en'], gpu=False) 

    # Fetch rows where identifier is missing
    cursor.execute("SELECT id, imagem FROM capturas WHERE identificador IS NULL")
    linhas = cursor.fetchall()

    if not linhas:
        print("[END] No new images to process in the database.")
        conn.close()
        return

    print(f"[INFO] Found {len(linhas)} images pending OCR processing.\n")

    # Image processing loop
    for linha in linhas:
        id_registro = linha[0]
        imagem_blob = linha[1]
        
        # Convert BLOB bytes back to OpenCV image
        nparr = np.frombuffer(imagem_blob, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print(f"[ERROR] Failed to decode image bytes for ID {id_registro}. Skipping...")
            continue
            
        # Run OCR extraction
        resultado_ocr = reader.readtext(img)
        textos_detectados = [res[1] for res in resultado_ocr]
        texto_final = " ".join(textos_detectados).strip()
        
        # Update database with results
        if texto_final:
            cursor.execute("UPDATE capturas SET identificador = ? WHERE id = ?", (texto_final, id_registro))
            conn.commit()
            print(f"✅ [ID {id_registro}] Saved text: '{texto_final}'")
        else:
            cursor.execute("UPDATE capturas SET identificador = ? WHERE id = ?", ("NOT DETECTED", id_registro))
            conn.commit()
            print(f"⚠️ [ID {id_registro}] No text detected in image.")

    conn.close()
    print("\n[END] All pending database records processed successfully!")

if __name__ == '__main__':
    processar_ocr_banco()