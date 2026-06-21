import cv2

# Caminho do seu vídeo de teste
VIDEO_PATH = '../videos/syntitic.mp4' 

cap = cv2.VideoCapture(VIDEO_PATH)
if cap:
    ret, frame = cap.read()

    if not ret:
        print("Erro: Não foi possível ler o vídeo. Verifique o caminho.")
        exit()

    print("---------------------------------------------------------")
    print("INSTRUÇÕES:")
    print("1. Clique e arraste o mouse sobre a saída da impressora.")
    print("2. Pressione ENTER ou ESPAÇO para confirmar.")
    print("3. Pressione 'c' se quiser cancelar e desenhar de novo.")
    print("---------------------------------------------------------")

    # Abre a janela para seleção
    bbox = cv2.selectROI("Selecione a area da impressora", frame, fromCenter=False, showCrosshair=True)
    cv2.destroyWindow("Selecione a area da impressora")

    x, y, w, h = bbox

    print("\n=== COPIE ESSES VALORES PARA O SEGUNDO SCRIPT ===")
    print(f"ROI_X = {x}")
    print(f"ROI_Y = {y}")
    print(f"ROI_W = {w}")
    print(f"ROI_H = {h}")
    print("=================================================")

    cap.release()