import os
import requests
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

TOKEN = os.getenv("OLHOVIVO_TOKEN")
print("Token lido:", TOKEN)
# Cria uma sessão - isso guarda o cookie automaticamente entre chamadas
session = requests.Session()

# Passo 1: Autenticação
url_auth = f"http://api.olhovivo.sptrans.com.br/v2.1/Login/Autenticar?token={TOKEN}"
resposta_auth = session.post(url_auth)

print("Status da autenticação:", resposta_auth.status_code)
print("Autenticado com sucesso?:", resposta_auth.text)

# Passo 2: Se autenticou, testa buscar as linhas de ônibus com "Butantã" no nome
if resposta_auth.text == "true":
    url_linhas = "http://api.olhovivo.sptrans.com.br/v2.1/Linha/Buscar?termosBusca=Butantã"
    resposta_linhas = session.get(url_linhas)
    print("\nResultado da busca de linhas:")
    print(resposta_linhas.json()[:3])  # mostra só as 3 primeiras pra não poluir o terminal
else:
    print("\nFalha na autenticação. Verifique se o token no .env está correto.")