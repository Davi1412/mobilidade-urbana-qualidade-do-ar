import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def conectar():
    conexao = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        client_encoding="utf8"
    )
    return conexao


if __name__ == "__main__":
    print("Host:", os.getenv("DB_HOST"))
    print("Port:", os.getenv("DB_PORT"))
    print("DB:", os.getenv("DB_NAME"))
    print("User:", os.getenv("DB_USER"))
    print("Password lida (tamanho):", len(os.getenv("DB_PASSWORD") or ""))

    try:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("SELECT nome FROM estacao_qualidade_ar;")
        resultado = cursor.fetchall()
        print("Conexão bem-sucedida. Estações cadastradas:")
        for linha in resultado:
            print("-", linha[0])
        cursor.close()
        conexao.close()
    except Exception as erro:
        print("Erro ao conectar:", repr(erro))