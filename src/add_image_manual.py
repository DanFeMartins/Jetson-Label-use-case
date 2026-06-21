import sqlite3
from datetime import datetime

# ================= CONFIGURAÇÕES =================
DB_PATH = 'etiquetas.db'
NOME_DA_IMAGEM = 'images/i.png'  # Altere para o caminho da sua imagem
# =================================================

def inserir_imagem_local(caminho_imagem):
    try:
        # 1. Abre a imagem no modo de leitura binária ('rb') e lê os bytes
        with open(caminho_imagem, 'rb') as arquivo:
            imagem_blob = arquivo.read()
        
        # 2. Conecta ao banco de dados
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 3. Pega o timestamp atual
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 4. Insere os dados na tabela (deixando a coluna 'identificador' como NULL para o OCR ler depois)
        cursor.execute(
            "INSERT INTO capturas (timestamp, imagem) VALUES (?, ?)", 
            (agora, imagem_blob)
        )
        
        # Salva as alterações e fecha a conexão
        conn.commit()
        conn.close()
        
        print(f"✅ Sucesso! A imagem '{caminho_imagem}' foi salva no banco de dados.")
        
    except FileNotFoundError:
        print(f"❌ Erro: O arquivo '{caminho_imagem}' não foi encontrado. Verifique o caminho.")
    except Exception as e:
        print(f"❌ Ocorreu um erro ao interagir com o banco de dados: {e}")

if __name__ == '__main__':
    inserir_imagem_local(NOME_DA_IMAGEM)