from firebase import initialize_firebase
from firebase import read_realtime_db, update_realtime_db, listen_realtime_db
from grbl import conectaPorta
from grbl import destravaGRBL


from taskManager import obtemFila
from taskManager import falhaTarefa
from taskManager import preparaComandos
from taskManager import processaTarefa

from commandManager import processaFilaComandos

from statusManager import reportaEstado
import time
import json

verbose = True
sleep = False
proximaConsultaTarefas = 0

pathTerreno = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/cartografia/" + pathTerreno + "/tarefas"
pathCanteiros = "/cartografia/" + pathTerreno + "/canteiros"
pathPlantas = "/cartografia/" + pathTerreno + "/plantas"
pathManejos = "/conhecimento/manejos"
pathDispositivo = "/cartografia/" + pathTerreno + "/dispositivos" + "/-OGxBHAFHCtr8V3P0-5F"
pathConfiguracao = pathDispositivo + "/configuracao"
pathFerramenta = pathDispositivo + "/ferramenta"

GRBLport = "/dev/ttyACM0"
HEADport = "/dev/ttyUSB0"
PUMPport = "/dev/ttyACM2"
baudrate = 115200  # Velocidade padrao do GRBL

config = {}
ferramenta = {}

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

    #conecta com os perifericos
    GRBL = conectaPorta(GRBLport, baudrate, "GRBL")
    HEAD = conectaPorta(HEADport, 9600, "HEAD")
    PUMP = conectaPorta(PUMPport, baudrate, "PUMP")

    # Listen to the "configuracoes" key in the realtime database
    def listenerConfig(event):
        if isinstance(event.data, dict):
            config.update(event.data)
        elif isinstance(event.data, str):
            config[event.path[1:]] = event.data
        elif isinstance(event.data, int):
            config[event.path[1:]] = event.data
        
        verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} Configurações atualizadas.")
        
    # Listen to the "ferramentas" key in the realtime database
    def listenerFerramentas(event):
        if isinstance(event.data, dict):
            ferramenta.update(event.data)
        else:
            ferramenta[event.path[1:]] = event.data

        verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} Ferramentas atualizadas.")

    def listenerTarefas(event):
        """
        Callback para monitorar mudancas nas tarefas.
        No caso de tarefas que tenham estado alterado ou criado como Aguardando,
        ou tarefas que tenham seu prazo definido para o passado,
        a funcao desperta o script
        """
        global proximaConsultaTarefas
        verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} Tarefa {event.path} atualizada")
        acordar = False
        
        # no caso de um event.data que seja um dicionario,
        # verifica as propriedades
        if isinstance(event.data, dict):
            # verifica se deve acordar por mudanca no estado
            if 'estado' in event.data and event.data['estado'] == "Aguardando":
                acordar = True
            # verifica se deve acordar por mudanca no prazo
            if 'programa' in event.data and 'prazo' in event.data['programa']:
                prazo_timestamp = event.data['programa']['prazo']
                if prazo_timestamp < round(time.time() * 1000):
                    acordar = True
                    
        # no caso de um event.data que seja um string
        # verifica o final do caminho
        elif event.path.endswith('/estado') and event.data == "Aguardando":
            acordar = True
        elif event.path.endswith('/prazo') and event.data < round(time.time() * 1000):
            acordar = True
    
        # acorda, se for o caso
        if acordar:
            proximaConsultaTarefas = 0
            verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} Acordando...")

    # Configura os listeners
    listen_realtime_db(pathConfiguracao, listenerConfig)
    listen_realtime_db(pathFerramenta, listenerFerramentas)
    listen_realtime_db(pathTarefas, listenerTarefas)

    #obtem a base de conhecimento atualizada
    manejos = read_realtime_db(pathManejos)
    canteiros = read_realtime_db(pathCanteiros)
    plantas = read_realtime_db(pathPlantas)

    proximoReporteEstado = 0

    while True:
        # Registra a hora de inicio do loop principal
        
        agora = time.time()
        # Verifica o estado dos periféricos e a atividade do robô. O robô está ativo
        # se algum dos periféricos não está em estado Idle. Se todos estiverem, ou
        # se nenhum periférico estiver instalado, ele está inativo
        estado = reportaEstado(GRBL, HEAD, PUMP, filaComandos, historicoComandos, sleep)

        # Verifica se ha estado de Alarme nos periféricos ou outra condicao que exija
        # acao de recuperacao
        recuperar = False
        if estado['GRBL']['estado'] == "Alarm":
            verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} Destravando alarme GRBL")
            destravaGRBL(GRBL, verbose)
            recuperar = True

        # Se foi realizada acao de recuperacao precisa atualizar o estado
        if recuperar: estado = reportaEstado(GRBL, HEAD, PUMP, filaComandos, historicoComandos, sleep)

        # Verifica se ha alguma atividade em andamento
        ativo = False
        if GRBL and estado["GRBL"]["estado"] == "Run": ativo = True
        #if HEAD and estado["HEAD"]["estado"] == "Run": ativo = True 
        #if PUMP and estado["PUMP"]["estado"] != "Idle": ativo = True TODO: manusear os estados dos demais perifericos

        # Verifica se deve dormir
        # Se ha atividade em andamento,comandos na fila, ou reporte de
        # estado necessario, deve ficar acordado.
        sleep = not (ativo or len(filaComandos)>0 or proximoReporteEstado <= agora)

        verbose and print(f"{time.strftime('%H:%M:%S')} {agora % 1:.6f} Loop principal iniciado. Ativo: {ativo}. Dormindo: {sleep}")
        
        if not sleep:
        # Se nao estiver dormindo, quer dizer que ha comandos na fila
        # ou alguma atividade em andamento ou, no minimo, deve reportar
        # o estado. Reportar o estado tem prioridade sobre o processamento
        # da fila
            
            # Reporta o estado se for necessario
            if proximoReporteEstado <= agora:
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} Enviando estado para o banco de dados")
                update_realtime_db(pathDispositivo + "/estado", estado)
                proximoReporteEstado = (agora + config["intervaloReporteEstadoAtivo"]) if ativo else (agora + config["intervaloReporteEstadoInativo"])
            
            # Processa a fila de comandos
            processaFilaComandos(GRBL, HEAD, PUMP, filaComandos, historicoComandos, True)
        
        else:
        # Se estiver dormindo, quer dizer que nao ha comandos na fila
        # nem alguma atividade em andamento. Vai dormir ate obter a,
        # tarefa da fila. Isso acontece por decurso de intervalo da
        # consulta, ou por acao do listener da chave de tarefas, que
        # adianta a proxima consulta

            # Consultar a fila de tarefas se for necessario
            if proximaConsultaTarefas <= agora:
                proximoReporteEstado = agora
                listaDeTarefas = obtemFila(manejos, config["loteConsulta"], ferramenta, verbose) #TODO: considerar que o GRBL ou HEAD podem estar offline
                proximaConsultaTarefas = agora + config["intervaloConsultaTarefas"]
                
                # Se a consulta retornar alguma tarefa, processa as instrucoes
                # e inclui na fila de comandos
                if len(listaDeTarefas):
                    for tarefa in listaDeTarefas[:config["loteProcessamento"]]:
                        # recupera dados da variante e objeto da tarefa
                        # em caso de objeto nao encontrado, marca falha na tarefa
                        # e continua o loop na prxima tarefa
                        # em caso de objeto nao definido, utiliza o default
                        varianteTarefa = manejos[tarefa["acao"]["manejoVinculado"]]["variante"][tarefa["acao"]["varianteVinculada"]]
                        objetoTarefa = {}
                        if tarefa["objeto"]["tipo"] == "planta":
                            try: objetoTarefa = plantas[tarefa["objeto"]["chave"]]
                            except: 
                                falhaTarefa(tarefa["key"], "Objeto da tarefa no encontrado.")
                                continue
                        
                        elif tarefa["objeto"]["tipo"] == "canteiro": 
                            try: objetoTarefa = canteiros[tarefa["objeto"]["chave"]]
                            except:
                                falhaTarefa(tarefa["key"], "Objeto da tarefa no encontrado.")
                                continue
                        else:
                            objetoTarefa = objetoDefault

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
                        
                else:
                # se nao houver for obtida nenhuma nova tarefa na consulta,
                # reporta no serial e continua dormindo
                    print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} Nenhuma tarefa disponível.")

            # espera o intervalo de frequencia do loop principal.
            time.sleep(config["baixaFrequencia"] if sleep else config["frequencia"])
