import sqlite3
import cv2
import numpy as np
import easyocr

# ================= CONFIGURAÇÕES =================
DB_PATH = '../database/etiquetas.db'
# =================================================

def processar_ocr_banco():
    # 1. Conecta ao banco de dados existente
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. Cria a coluna 'identificador' caso ela ainda não exista na tabela
    try:
        cursor.execute("ALTER TABLE capturas ADD COLUMN identificador TEXT")
        conn.commit()
        print("[INFO] Coluna 'identificador' adicionada à tabela 'capturas'.")
    except sqlite3.OperationalError:
        # Se a coluna já existir, o SQLite joga um erro que podemos ignorar com segurança
        print("[INFO] A coluna 'identificador' já existe. Prosseguindo...")

    # 3. Inicializa o motor do EasyOCR (Configurado para Português e Inglês)
    print("[INFO] Inicializando a inteligência artificial do OCR...")
    # Se você tiver uma GPU Nvidia configurada com CUDA, altere para gpu=True para ser ultra rápido
    reader = easyocr.Reader(['pt', 'en'], gpu=False) 

    # 4. Busca apenas as linhas onde o identificador ainda é nulo (evita retrabalho)
    cursor.execute("SELECT id, imagem FROM capturas WHERE identificador IS NULL")
    linhas = cursor.fetchall()

    if not linhas:
        print("[FIM] Nenhuma imagem nova para processar no banco de dados.")
        conn.close()
        return

    print(f"[INFO] Encontradas {len(linhas)} imagens aguardando leitura de OCR.\n")

    # 5. Loop para processar cada imagem capturada
    for linha in linhas:
        id_registro = linha[0]
        imagem_blob = linha[1]
        
        # Converte os bytes do BLOB de volta para um array que o OpenCV/EasyOCR entendem
        nparr = np.frombuffer(imagem_blob, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print(f"[ERRO] Falha ao decodificar os bytes da imagem do ID {id_registro}. Pulando...")
            continue
            
        # Executa a mágica do OCR potente na imagem
        # O EasyOCR lida muito bem com ruídos, mas se as etiquetas forem muito escuras,
        # você pode descomentar a linha abaixo para testar em escala de cinza:
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        resultado_ocr = reader.readtext(img)
        
        # O resultado vem em uma lista de tuplas: (caixa_delimitadora, texto, confiança)
        # Vamos extrair apenas os textos detectados e juntá-los com um espaço
        textos_detectados = [res[1] for res in resultado_ocr]
        texto_final = " ".join(textos_detectados).strip()
        
        # 6. Atualiza a linha correspondente no banco de dados
        if texto_final:
            cursor.execute("UPDATE capturas SET identificador = ? WHERE id = ?", (texto_final, id_registro))
            conn.commit()
            print(f"✅ [ID {id_registro}] Texto salvo: '{texto_final}'")
        else:
            # Caso a imagem esteja totalmente ilegível ou borrada
            cursor.execute("UPDATE capturas SET identificador = ? WHERE id = ?", ("NÃO DETECTADO", id_registro))
            conn.commit()
            print(f"⚠️ [ID {id_registro}] Nenhum texto pôde ser lido na imagem.")

    # Fecha a conexão de forma segura
    conn.close()
    print("\n[FIM] Todo o banco de dados pendente foi populado com sucesso!")

if __name__ == '__main__':
    processar_ocr_banco()