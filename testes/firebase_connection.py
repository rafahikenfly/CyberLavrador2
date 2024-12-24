import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import time

# Configuração inicial
def initialize_firebase():
    # Substitua pelo caminho do seu arquivo JSON
    cred_path = "../../microagricultura-firebase-key.json"
    cred = credentials.Certificate(cred_path)
    
    # Para Realtime Database
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://microagricultura-fbdc5-default-rtdb.firebaseio.com/'
    })
    
# Função para interagir com o Realtime Database
def push_realtime_db(path, data):
    ref = db.reference(path)
    ref.push(data)
    print("Dados enviados para o Realtime Database:", data)

def update_realtime_db(path, data):
    ref = db.reference(path)
    ref.update(data)
    print("Dados atualizados no Realtime Database:", data)

def write_realtime_db(path, data):
    ref = db.reference(path)
    ref.set(data)
    print("Dados sobreescritos no Realtime Database:", data)

def read_realtime_db(path):
    """
    Le o valor de uma chave especifica do Firebase.
    :param path: Caminho da chave no banco de dados.
    :return: Valor da chave ou None se nao existir.
    """
    try:
        ref = db.reference(path)
        value = ref.get()
        print(f"Valor da chave '{path}': {value}")
        return value
    except Exception as e:
        print(f"Erro ao ler a chave '{path}': {e}")
        return None

def listen_realtime_db(path):
    """
    Monitora mudancas em uma chave especifica no Firebase.
    :param path: Caminho da chave no banco de dados para monitorar.
    """
    ref = db.reference(path)

    def listener(event):
        # Imprime o novo valor quando ha mudanaas
        print(f"Alteracao {event.event_type} em {event.path} para {event.data}")

    # Adiciona o listener para a referencia
    print(f"Monitorando alteracoes na chave: {path}")
    ref.listen(listener)

if __name__ == "__main__":
    initialize_firebase()
    # Enviar dados para o Realtime Database
    push_realtime_db("testes/raspberry/push", time.time())
    # Le dados do Realtime Database
    read_realtime_db("testes/raspberry/read")
    # Atualiza os dados do Realtime Database
    dados = { "agora": time.time() }    
    update_realtime_db("testes/raspberry/read", dados)
    # Sobreescreve os dados do Realtime Database
    dados = { "sobreescrito": 0}
    write_realtime_db("testes/raspberry/read", dados)
    # Escuta uma chave do Realtime Database
    listen_realtime_db("testes/raspberry/listen")
