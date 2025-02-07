import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning

import time

# Configuração inicial
def initialize_firebase():
    # cred_path = "/Users/rcmachado/Documents/GitHub/microagricultura-firebase-key.json"
    cred_path = "../../microagricultura-firebase-key.json"
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://microagricultura-fbdc5-default-rtdb.firebaseio.com/'
    })
    logInfo("Firebase iniciado.")
    
# Função para interagir com o Realtime Database
def push_realtime_db(path, data, verbose = False):
    ref = db.reference(path)
    newRef = ref.push(data)
    logInfo("Dados enviados para o Realtime Database")
    if verbose: logDebug(data)
    return newRef.key

def update_realtime_db(path, data, verbose = False):
    ref = db.reference(path)
    ref.update(data)
    logInfo("Dados enviados para o Realtime Database")
    if verbose: logDebug(data)

def write_realtime_db(path, data, verbose):
    ref = db.reference(path)
    ref.set(data)
    logInfo("Dados enviados para o Realtime Database")
    if verbose: logDebug(data)

def read_filtered_realtime_db(path, filterProp, value, limit = 100):
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
        consulta = ref.order_by_child(filterProp).equal_to(value).limit_to_first(limit).get() or {}
        return consulta
    except Exception as e:
        logError(f"Erro ao ler a chave '{path}': {e}")
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
        logError(f"Erro ao ler a chave '{path}': {e}")
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
        logError(f"Erro ao ler a chave '{path}': {e}")
        return None


def listen_realtime_db(path, listener):
    """
    Monitora mudancas em uma chave especifica no Firebase.
    :param path: Caminho da chave no banco de dados para monitorar.
    :param path: Caminho da chave no banco de dados para monitorar.
    """
    ref = db.reference(path)

    logInfo(f"Monitorando alteracoes na chave: {path}")
    ref.listen(listener)
