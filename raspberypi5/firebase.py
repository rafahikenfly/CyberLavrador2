import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Configuração inicial
def initialize_firebase():
    # cred_path = "/Users/rcmachado/Documents/GitHub/microagricultura-firebase-key.json"
    cred_path = "../../microagricultura-firebase-key.json"
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://microagricultura-fbdc5-default-rtdb.firebaseio.com/'
    })
    print("Firebase iniciado")
    
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

def read_filtered_realtime_db(path, filter, value, limit):
    """
    Le o valor de uma chave especifica do Firebase.
    :param path: Caminho da chave no banco de dados.
    :param filter: chave para filtrar a busca.
    :param value: valor para a busca.
    :param limit: limite de resultados.
    :return: Valor da chave ou None se nao existir.
    """
    try:
        ref = db.reference(path)
        consulta = ref.order_by_child(filter).equal_to(value).limit_to_first(limit).get() or {}
        return consulta
    except Exception as e:
        print(f"Erro ao ler a chave '{path}': {e}")
        return None

def read_ordered_realtime_db(path, order, limit):
    """
    Le o valor de uma chave especifica do Firebase.
    :param path: Caminho da chave no banco de dados.
    :param order: chave para ordenar a busca.
    :param limit: limite de resultados.
    :return: Valor da chave ou None se nao existir.
    """
    try:
        ref = db.reference(path)
        consulta = ref.order_by_child(order).limit_to_first(limit).get()
        return consulta
    except Exception as e:
        print(f"Erro ao ler a chave '{path}': {e}")
        return None

def read_realtime_db(path):
    """
    Le o valor de uma chave especifica do Firebase.
    :param path: Caminho da chave no banco de dados.
    :return: Valor da chave ou None se nao existir.
    """
    try:
        ref = db.reference(path)
        value = ref.get()
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
