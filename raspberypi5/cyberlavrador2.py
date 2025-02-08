from firebase import initialize_firebase
from firebase import read_realtime_db, update_realtime_db, listen_realtime_db
from comunicacao import conectaPorta
from grbl import desativaAlarme

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning

from taskManager import obterFilaTarefas
from taskManager import obterInformacoesTarefa
from taskManager import marcaFalhaTarefa
from taskManager import interpretarInstrucoes
from taskManager import marcaTarefaProcessada
from taskManager import otimizaFilaTarefas

from commandManager import processaFila
from commandManager import recuperaComandos
from commandManager import processaErroGCode

from handlerEstado import estadoRobo
import time

verbose = True
dormindo = False
proximaConsultaTarefas = 0
GRBLBuffer = 16

pathTerreno = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/tarefas/" + pathTerreno
pathCanteiros = "/canteiros/" + pathTerreno
pathPlantas = "/plantas/" + pathTerreno

pathManejos      = "/conhecimento/manejos"
pathVariantes    = "/conhecimento/variantes"
pathDispositivo  = "/cartografia/" + pathTerreno + "/dispositivos" + "/-OGxBHAFHCtr8V3P0-5F"
pathConfiguracao = pathDispositivo + "/configuracao"
pathFerramenta   = pathDispositivo + "/ferramenta"


config = {}
definicoesFerramental = {}
manejos = {}
variantes = {}
canteiros = {}
plantas = {}


filaGCode = []
historicoGCode = []
tarefaAtual = ""
inicioTarefaAtual = 0

def inicializaRobo() :
    # inicializa o robo, conectando o firebase com seus listeners
    # e conectando os perifericos

    #TODO: utilizar configurações dos periféricos registradas no firebase
    GRBLport = "/dev/ttyACM0"
    HEADport = "/dev/ttyUSB0"
    PUMPport = "/dev/ttyACM2"
    GRBLbaudrate = 115200  # Velocidade padrao do GRBL
    HEADbaudrate = 9600
    PUMPbaudrate = 9600

    initialize_firebase()

    #conecta com os perifericos
    global GRBL
    global HEAD
    global PUMP
    GRBL = conectaPorta(GRBLport, GRBLbaudrate, "GRBL")
    HEAD = conectaPorta(HEADport, HEADbaudrate, "HEAD")
    PUMP = conectaPorta(PUMPport, PUMPbaudrate, "PUMP")

    # Listener das "configuracoes" no realtime database
    def listenerConfig(event):
        if isinstance(event.data, dict):
            config.update(event.data)
        elif isinstance(event.data, str):
            config[event.path[1:]] = event.data
        elif isinstance(event.data, int):
            config[event.path[1:]] = event.data
        logInfo("Configurações atualizadas do RTDB.")
        logDebug(config)
        
    # Listener das "ferramentas" no realtime database
    def listenerFerramentas(event):
        if isinstance(event.data, dict):
            definicoesFerramental.update(event.data)
        else:
            definicoesFerramental[event.path[1:]] = event.data
        logInfo("Ferramentas atualizadas do RTDB.")
        logDebug(definicoesFerramental)

    # Listener das "tarefas" no realtime database
    def listenerTarefas(event):
        """
        Callback para monitorar mudancas nas tarefas.
        No caso de tarefas que tenham estado alterado ou criado como Aguardando,
        ou tarefas que tenham seu prazo definido para o passado,
        a funcao desperta o script
        """
        global proximaConsultaTarefas
        logInfo(f"Tarefa atualizada: {event.path}")
        acordar = False
        
        # no caso de um event.data que seja um dicionario,
        # verifica as propriedades
        if isinstance(event.data, dict):
            # verifica se deve acordar por mudanca no estado
            if 'estado' in event.data and event.data['estado'] == "aguardando":
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
            logInfo("Acordando para verificar tarefas...")

    # Configura os listeners
    listen_realtime_db(pathConfiguracao, listenerConfig)
    listen_realtime_db(pathFerramenta, listenerFerramentas)
    listen_realtime_db(pathTarefas, listenerTarefas)

def reestabeleceRobo():
    filaComandos = recuperaComandos("fila_comandos.pkl")
    if len(filaComandos):
        logInfo(f"Recuperados {len(filaComandos)} comandos pendentes da ultima execucao")
        historicoComandos = recuperaComandos("hitorico_comandos.pkl")
        if len(historicoComandos):
            logInfo(f"Recuperados {len(historicoComandos)} comandos executados na ultima execucao")
        processaErroGCode("Robo reiniciado", filaComandos, historicoComandos)

def atualizaConhecimento():
    #obtem a base de conhecimento atualizada
    global manejos
    global variantes
    global canteiros
    global plantas
    manejos = read_realtime_db(pathManejos)
    variantes = read_realtime_db(pathVariantes)
    canteiros = read_realtime_db(pathCanteiros)
    plantas = read_realtime_db(pathPlantas)

if __name__ == "__main__":
    inicializaRobo()
    reestabeleceRobo()
    atualizaConhecimento()

    proximoReporteEstado = 0
    while True:
        # Registra a hora de inicio do loop principal
        agora = roundtime.time()

        # Obtem o estado dos periféricos e a atividade do robô. E verifica se ha estado
        # de Alarme nos periféricos ou outra condicao que exija acao de recuperacao.
        estado = estadoRobo(GRBL, HEAD, PUMP, filaGCode, historicoGCode, dormindo)
        recuperar = False
        if estado['GRBL']['estado'] == "Alarm":
            # Um estado de Alarme do GRBL exige uma ação de destravamento.
            logWarning( "GRBL em estado de alarme. Desativando alarme GRBL")
            desativaAlarme(GRBL)
            recuperar = True
        # Se foi realizada acao de recuperacao precisa atualizar o estado
        if recuperar: estado = estadoRobo(GRBL, HEAD, PUMP, filaGCode, historicoGCode, dormindo)

        # Verifica se ha alguma atividade em andamento. O robô está ativo
        # se algum dos periféricos não está em estado Idle. Se todos estiverem, ou
        # se nenhum periférico estiver instalado, ele está inativo
        ativo = False
        if GRBL and estado["GRBL"]["estado"] == "Run": ativo = True
        #if HEAD and estado["HEAD"]["estado"] == "Run": ativo = True 
        #if PUMP and estado["PUMP"]["estado"] != "Idle": ativo = True TODO: manusear os estados dos demais perifericos

        # Verifica se deve dormir
        # Se ha atividade em andamento,comandos na fila, ou reporte de
        # estado necessario, deve ficar acordado.
        dormindo = not (ativo or len(filaGCode)>0)

        # Loga o início do loop principal
        logDebug(f"Loop principal iniciado. Ativo: {ativo}. Dormindo: {dormindo}")

        # Se for necessario, reporta o estado no RTD
        if agora > proximoReporteEstado:
            logInfo("Enviando estado para o banco de dados")
            update_realtime_db(pathDispositivo + "/estado", estado)
            proximoReporteEstado = min((proximaConsultaTarefas, agora + config["intervaloReporteEstadoInativo"]) if dormindo else (agora + config["intervaloReporteEstadoAtivo"]))

        if not dormindo:
        # Se nao estiver dormindo, quer dizer que ha comandos na fila
        # ou alguma atividade em andamento. Independente do caso, deve
        # processar a fila de comandos, pois pode ser possível enviar
        # um novo comando.
            processaFila(filaGCode, historicoGCode, GRBL, estado["GRBL"]["lookahead_buffer"], HEAD, PUMP, )
        
        else:
        # Se estiver dormindo, quer dizer que nao ha comandos na fila
        # nem alguma atividade em andamento. O robo vai continuara doemindo
        # ate obter uma nova tarefa da fila. Isso acontece ou pelo decurso de
        # intervalo da consulta de tarefas ou por acao do listener da chave de
        # tarefas, que adianta a proxima consulta. De qualquer modo, isso
        # acontece quando agora > proxima Consulta.

            # Se necessário, consulta a fila de tarefas
            if agora > proximaConsultaTarefas:
                listaDeTarefas = obterFilaTarefas(manejos, config['loteConsulta'], definicoesFerramental) #TODO: considerar que o GRBL ou HEAD podem estar offline
                proximaConsultaTarefas = agora + config['intervaloConsultaTarefas']
                
                if len(listaDeTarefas):
                # Se a consulta retornar alguma tarefa, otimiza a fila e processa
                # as instrucoes de cada uma das tarefas, incluindo na fila de comandos
                    listaOtimizada = otimizaFilaTarefas(listaDeTarefas, config['lookahead_buffer'])
                    for tarefa in listaOtimizada:
                        # Recupera dados da variante e objeto da tarefa
                        # se houver algum problema com a recuperação das informações
                        # falha a tarefa como registrando o motivo.
                        info = obterInformacoesTarefa(tarefa, variantes, plantas, canteiros)
                        if not info[0]: marcaFalhaTarefa(tarefa['key'], info[1])
                        else:
                            for gcode in interpretarInstrucoes(info[1], info[2]):
                            # Para cada instrucao com as tags processadas da variante,
                            # inclui um gcode na fila.
                                filaGCode.append({
                                    'tarefa': tarefa['key'],
                                    'gcode': gcode,
                                    'resposta': '',
                                })
                            marcaTarefaProcessada(tarefa['key'])
                else:
                # Se a consulta não retornar nenhuma tarefa, continua dormindo
                    logInfo(f"Nenhuma tarefa disponível.")

        # espera o intervalo de frequencia do loop principal.
        time.sleep(config["baixaFrequencia"] if dormindo else config["frequencia"])

# o processamento da fila espera:
            # - GRBL desconectado --> aguarda o próximo loop (espera reestabelecer conexão)
            # - GRBL em alarme    --> aguarda o próximo loop (espera destravar GRBL)
            # - buffer GRBL cheio --> aguarda o próximo loop (espera liberar buffer)
            # - HEAD desconectado --> aguarda o próximo loop (espera reestabelecer conexão)
