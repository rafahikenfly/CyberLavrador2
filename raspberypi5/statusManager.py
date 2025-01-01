from grbl import enviaGCode
import time

def reportaEstado(GRBL, HEAD, filaComandos, historicoComandos):
    resposta = enviaGCode(GRBL, "?")
    estadoGRBL = resposta[1] if resposta[0] else {"estado": "offline"}
    resposta = enviaGCode(HEAD, "?")
    estadoHEAD = resposta[1] if resposta[0] else {"estado": "offline"}

    estado = {
        "hora": time.time(),
        "GRBL": estadoGRBL,
        "HEAD": estadoHEAD,
        "filaAtual": len(filaComandos),
        "comandosExecutados": len(historicoComandos),
    }
    return estado