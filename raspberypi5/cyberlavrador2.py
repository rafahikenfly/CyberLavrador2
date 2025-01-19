from config import QUEUE
from firebase import initialize_firebase
from firebase import read_realtime_db, update_realtime_db, listen_realtime_db
from grbl import conectaPorta
from grbl import destravaGRBL

from taskManager import obtemFila
from taskManager import preparaComandos
from taskManager import processaTarefa

from commandManager import processaFilaComandos

from statusManager import reportaEstado
import time
import json

verbose = True

pathTerreno = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/cartografia/" + pathTerreno + "/tarefas"
pathCanteiros = "/cartografia/" + pathTerreno + "/canteiros"
pathPlantas = "/cartografia/" + pathTerreno + "/plantas"
pathManejos = "/conhecimento/manejos"
pathDispositivo = "/cartografia/" + pathTerreno + "/dispositivos" + "/-OGxBHAFHCtr8V3P0-5F"
pathConfiguracao = pathDispositivo + "/configuracao"

GRBLport = "/dev/ttyACM0"
HEADport = "/dev/ttyUSB0"
PUMPport = "/dev/ttyACM2"
baudrate = 115200  # Velocidade padrao do GRBL

config = {}

filaComandos = []
historicoComandos = []
objetoDefault = { "posicao": {
    "X": 100,
    "Y": 90,
    "Z": 80,
}}

if __name__ == "__main__":
    #inicializa firebase
    initialize_firebase()

    #conecta com o GRBL
    GRBL = conectaPorta(GRBLport, baudrate)
    HEAD = conectaPorta(HEADport, 9600)
    PUMP = conectaPorta(PUMPport, baudrate)

    # Listen to the "configuracoes" key in the realtime database
    def listener(event):
        if isinstance(event.data, dict):
            config.update(event.data)
        elif isinstance(event.data, str):
            config[event.path[1:]] = event.data
        elif isinstance(event.data, int):
            config[event.path[1:]] = event.data
        
        verbose and print("Configurações atualizadas:", config)

    # Set up the listener for the "configuracoes" key
    listen_realtime_db(pathConfiguracao, listener)

    #obtem a base de conhecimento atualizada
    manejos = read_realtime_db(pathManejos)
    canteiros = read_realtime_db(pathCanteiros)
    plantas = read_realtime_db(pathPlantas)

    proximaConsultaTarefas = 0
    proximoReporteEstado = 0

    while True:
        agora = time.time()
        verbose and print(agora, "Loop principal iniciado.")
        # Verifica o estado dos periféricos e a atividade do robô. O robô está ativo
        # se algum dos periféricos não está em estado Idle. Se todos estiverem, ou
        # se nenhum periférico estiver instalado, ele está inativo
        estado = reportaEstado(GRBL, HEAD, PUMP, filaComandos, historicoComandos)
        ativo = False
        if GRBL: ativo = estado[GRBL][estado] != "Idle"
        if HEAD: ativo = estado[HEAD][estado] != "Idle"
        if PUMP: ativo = estado[HEAD][estado] != "Idle"

#        verbose and print("Estado", estado)

        #TODO: verificar se algum periférico está em estado de alarme
        if estado['GRBL']['estado'] == "Alarm":
            verbose and print("Destravando alarme GRBL")
            destravaGRBL(GRBL)

        # verifica se é hora de reportar o estado e reporta, se for o caso
        if proximoReporteEstado <= agora:
            verbose and print("Estado", reportaEstado(GRBL, HEAD, PUMP, filaComandos, historicoComandos))
            update_realtime_db(pathDispositivo+"/estado", estado)
            proximoReporteEstado = agora + config["intervaloReporteEstadoAtivo"] + (0 if ativo else config["intervaloReporteEstadoInativo"])
        # verifica se é hora de consultar a fila de tarefas e processa fila se for o caso
        if proximaConsultaTarefas <= agora:
            listaDeTarefas = obtemFila(manejos, verbose) #TODO: considerar que o GRBL ou HEAD podem estar offline
            proximaConsultaTarefas = agora + config["intervaloConsultaTarefas"]
            # processa a consulta, reiniciando o loop principal caso não haja novas tarefas
            if len(listaDeTarefas) == 0:
                print("Nenhuma tarefa disponível.")
                continue

            # já se há tarefas, para cada tarefa,
            # prepara os comandos e marca a tarefa como processada
            for tarefa in listaDeTarefas[:QUEUE["loteProcessamento"]]:
                # recupera dados da variante da tarefa
                varianteTarefa = manejos[tarefa["acao"]["manejoVinculado"]]["variante"][tarefa["acao"]["varianteVinculada"]]
                # recupera dados do objeto da tarefa
                objetoTarefa = {}
                if tarefa["objeto"]["tipo"] == "planta":
                    objetoTarefa = plantas[tarefa["objeto"]["chave"]]
                elif tarefa["objeto"]["tipo"] == "canteiro": 
                    objetoTarefa = canteiros[tarefa["objeto"]["chave"]]
                else:
                    objetoTarefa = objetoDefault
                    #objetoTarefa é a planta[tarefa["objeto"]["chave"]]

                # para cada instrucao na variante, inclui um comando na fila.
                # Ao incluir um comando, as tags do código são processadas.
                for instrucao in preparaComandos(varianteTarefa, objetoTarefa):
                    filaComandos.append({
                        "tarefa": tarefa["key"],
                        "instrucao": instrucao,
                        "resposta": "",
                        "estado": "fila",
                    })
                processaTarefa(tarefa["key"])

        # se houver periferico disponível, processa a fila de comandos
        if not ativo:
            processaFilaComandos(GRBL, HEAD, PUMP, filaComandos, historicoComandos, True)
        
        # espera o intervalo de frequencia do loop princiapl.
        time.sleep(min(config["intervaloConsultaTarefas"], config["intervaloReporteEstadoAtivo"] + (0 if ativo else config["intervaloReporteEstadoInativo"]), config["frequencia"]))
