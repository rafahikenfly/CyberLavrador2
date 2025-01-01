from config import QUEUE
from firebase import initialize_firebase
from firebase import read_realtime_db, update_realtime_db
from grbl import conectaPorta
from grbl import destravaGRBL

from taskManager import obtemFila
from taskManager import preparaComandos
from taskManager import processaTarefa

from commandManager import processaFilaComandos

from statusManager import reportaEstado
import time

verbose = True

terrain = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/loteamento/"+ terrain + "/tarefas"
pathCanteiros = "/loteamento/"+ terrain + "/canteiros"
pathBOK = "/bok/classes"
pathDispositivo = "/loteamento/"+ terrain + "/dispositivos" + "/-cyberlavrador"

GRBLport = "/dev/ttyACM0"
HEADport = "/dev/ttyACM1"
PUMPport = "/dev/ttyACM2"
baudrate = 115200  # Velocidade padrao do GRBL

intervaloConsultaTarefas = 15
intervaloReporteEstado = 5
frequencia = 1

filaComandos = []
historicoComandos = []
objetoTeste = { "posicao": {
    "X": 100,
    "Y": 90,
    "Z": 80,
}}

if __name__ == "__main__":
    #inicializa firebase
    initialize_firebase()

    #conecta com o GRBL
    GRBL = conectaPorta(GRBLport, baudrate)
    HEAD = conectaPorta(HEADport, baudrate)
    PUMP = conectaPorta(PUMPport, baudrate)

    #obtem a base de conhecimento atualizada
    classes = read_realtime_db(pathBOK)
    canteiros = read_realtime_db(pathCanteiros)

    proximaConsultaTarefas = 0
    proximoReporteEstado = 0

    while True:
        agora = time.time()
        verbose and print(agora, "Loop principal iniciado.")
        # verifica o estado dos periféricos
        estado = reportaEstado(GRBL, HEAD, filaComandos, historicoComandos)

        #TODO: verificar se algum periférico está em estado de alarme
        if estado['GRBL']['estado'] == "Alarm":
            verbose and print("Destravando alarme GRBL")
            destravaGRBL(GRBL)

        # verifica se é hora de reportar o estado e reporta, se for o caso
        if proximoReporteEstado <= agora:
            verbose and print("Estado", reportaEstado(GRBL, HEAD, filaComandos, historicoComandos))
            update_realtime_db(pathDispositivo+"/estado", estado)
            proximoReporteEstado = agora + intervaloReporteEstado
        # verifica se é hora de consultar a fila de tarefas e processa fila se for o caso
        if proximaConsultaTarefas <= agora:
            listaDeTarefas = obtemFila(classes, verbose) #TODO: considerar que o GRBL ou HEAD podem estar offline
            proximaConsultaTarefas = agora + intervaloConsultaTarefas
            # processa a consulta, reiniciando o loop caso não haja novas tarefas
            if len(listaDeTarefas) == 0:
                print("Nenhuma tarefa disponível.")
                continue
            #para as tarefas da lista, prepara os comandos e marca a tarefa como processada
            for tarefa in listaDeTarefas[:QUEUE.get("loteProcessamento")]:
                for instrucao in preparaComandos(classes.get(tarefa.get("classe")).get("manejo").get(tarefa.get("manejo")), canteiros.get(tarefa.get("objeto"))):
                    filaComandos.append({
                        "tarefa": tarefa.get("chave"),
                        "instrucao": instrucao,
                        "resposta": "",
                        "estado": "fila",
                    })
                processaTarefa(tarefa.get("chave"))

        #se houver periferico disponível, processa a fila de comandos
        if True: #estado["GRBL"]["estado"] == "Idle" or estado["HEAD"]["estado"] == "Idle":
            processaFilaComandos(GRBL, HEAD, PUMP, filaComandos, historicoComandos, True)
        time.sleep(min(intervaloConsultaTarefas, intervaloReporteEstado,frequencia))
