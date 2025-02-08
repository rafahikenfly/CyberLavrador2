from comunicacao import enviaGCode
import time
from firebase import update_realtime_db
from config import logInfo


def estadoRobo(GRBL, HEAD, PUMP, filaComandos, historicoComandos, sleep):
    estadoGRBL = {"estado": "Desligado"}
    estadoHEAD = {"estado": "Desligado"}
    estadoPUMP = {"estado": "Desligado"}
    if GRBL:
        resposta = enviaGCode(GRBL, "?")
        estadoGRBL = resposta[1] if resposta[0] else {"estado": "Offline"}
    if HEAD:
        resposta = enviaGCode(HEAD, "?")
        estadoHEAD = resposta[1] if resposta[0] else {"estado": "Offline"}
    if PUMP:
        resposta = enviaGCode(PUMP, "?")
        estadoHEAD = resposta[1] if resposta[0] else {"estado": "Offline"}

    estado = {
        "dormindo": sleep,
        "hora": round(time.time()*1000),
        "GRBL": estadoGRBL,
        "HEAD": estadoHEAD,
        "PUMP": estadoPUMP,
        "tarefaAtual": filaComandos[0]["tarefa"] if len(filaComandos) else "",
        "filaAtual": len(filaComandos),
        "comandosExecutados": len(historicoComandos),
    }
    return estado