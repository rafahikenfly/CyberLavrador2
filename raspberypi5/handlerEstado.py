from comunicacao import enviaGCode
from grbl import obterEstadoGRBL
from head import obterEstadoHEAD
import time
from firebase import update_realtime_db
from config import logInfo


def estadoRobo(GRBL, HEAD, PUMP, filaTarefas, tarefaAtual, filaGCode, sleep):
    estadoGRBL = {
        'estado': 'Desligado',
        'lookahead_buffer': 0,
        }
    estadoHEAD = {"estado": "Desligado"}
    estadoPUMP = {"estado": "Desligado"}
    if GRBL:
        resposta = obterEstadoGRBL(GRBL)
        estadoGRBL = resposta if resposta else {
            'estado': 'Offline',
            'lookahead_buffer': 0,
        }
    if HEAD:
        resposta = obterEstadoHEAD(HEAD)
        estadoHEAD = resposta if resposta else {
            'estado': 'Offline',
            'lookahead_buffer': 0,
            }
    if PUMP:
        resposta = enviaGCode(PUMP, "?")
        estadoHEAD = resposta[1] if resposta[0] else {"estado": "Offline"}

    estado = {
        'dormindo': sleep,
        'hora': round(time.time()) * 1000,
        'GRBL': estadoGRBL,
        'HEAD': estadoHEAD,
        'PUMP': estadoPUMP,
        'numTarefasFila': len(filaTarefas),
        'tarefaAtual': tarefaAtual,
        'numGCodeFila': len(filaGCode),
    }
    return estado
