from firebase import initialize_firebase
from firebase import read_realtime_db, update_realtime_db, listen_realtime_db, read_filtered_realtime_db
from comunicacao import conectaPorta
from grbl import desativaAlarme

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning

from gestorListaTarefas import filtrarFilaTarefas
from gestorListaTarefas import ordenarTarefasPorChave
from gestorListaTarefas import obterInformacoesTarefa
from gestorListaTarefas import interpretarInstrucoes
from gestorListaTarefas import marcaTarefaProcessada
from gestorListaTarefas import marcaTarefaConcluida
from gestorListaTarefas import marcaFalhaTarefa

from commandManager import processaFilaGCode
from commandManager import recuperaComandos
from commandManager import processaErroGCode

from handlerEstado import estadoRobo
import time

pathTerreno = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/tarefas/" + pathTerreno
pathCanteiros = "/canteiros/" + pathTerreno
pathPlantas = "/plantas/" + pathTerreno

pathManejos      = "/conhecimento/manejos"
pathVariantes    = "/conhecimento/variantes"
pathDispositivo  = "/cartografia/" + pathTerreno + "/dispositivos" + "/-OGxBHAFHCtr8V3P0-5F"
pathConfiguracao = pathDispositivo + "/configuracao"
pathFerramenta   = pathDispositivo + "/ferramenta"

# variáveis de conhecimento
config = {}
ferramentas = {}
manejos = {}
variantes = {}
canteiros = {}
plantas = {}

# vaariáveis de operacao
filaTarefas = []
proximaConsultaTarefas = 0
tarefaAtual = {}
minInicioTarefaAtual = 0
filaGCode = []
posFilaGCode = 0
dormindo = True

def inicializarRobo() :
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
            ferramentas.update(event.data)
        else:
            ferramentas[event.path[1:]] = event.data
        logInfo("Ferramentas atualizadas do RTDB.")
        logDebug(ferramentas)

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

def reestabelecerRobo():
    recover = recuperaComandos("comandos.pkl")
    if len(recover[0]):
        logInfo(f"Recuperados {len(recover[0])} comandos da execucao da tarefa {recover[1]}")
        global filaGCode
        global tarefaAtual
        filaGCode = recover[0]
        tarefaAtual = recover[1]

def atualizarConhecimento():
    #obtem a base de conhecimento atualizada
    global manejos
    global variantes
    global canteiros
    global plantas
    manejos = read_realtime_db(pathManejos)
    variantes = read_realtime_db(pathVariantes)
    canteiros = read_realtime_db(pathCanteiros)
    plantas = read_realtime_db(pathPlantas)

def reportaEstadoRTD(estado):
    logInfo("Enviando estado para o banco de dados")
    logDebug(estado)
    update_realtime_db(pathDispositivo + "/estado", estado)
    global proximoReporteEstado
    proximoReporteEstado = round(agora) * 1000 + config['intervaloReporteEstadoInativo'] if dormindo else round(agora) * 1000 + + config['intervaloReporteEstadoAtivo']
    proximoReporteEstado = min(proximaConsultaTarefas,proximoReporteEstado)

def obterFilaTarefas():
    """
    :return array: Retorna um novo array com as tarefas obtidas a partir do RTD.
    Está implementada a filtragem por prazo, condições e ferramentas
    """
    try:
        #Busca a lista de tarefas, respeitando o lote de consulta
        #Apenas as tarefas com estado Aguardando interessam
        tarefasRTD = read_filtered_realtime_db (pathTarefas, "estado", "aguardando", config['loteConsulta'])
        logDebug(f"{len(tarefasRTD)} tarefa(s) com estado Aguardando no lote.")
        returnArr = filtrarFilaTarefas(tarefasRTD, manejos, ferramentas)
        return returnArr
    except Exception as e:
        logError(f"Erro ao obter fila de tarefas: {e}")
        return []

def otimizarFilaTarefas():
    """"
    : return array: Retorna um novo array com as tarefas em ordem otimizada
    Está implementada a ordenação por prazo
    """
    returnArr = ordenarTarefasPorChave(filaTarefas[:config['lookahead_buffer']],"programa","prazo")
    logDebug(f"Fila de tarefas com {len(filaTarefas)} tarefa(s) otimizada.")
    return returnArr

def processarProximaTarefa():
    if len(filaTarefas): # Se a fila de tarefas não estiver vazia, recupera 
                         # a primeira tarefa da fila e registra o horário de
                         # início do processamento, para registrar o tempo
                         # de execução quando a tarefa for concluída
        global tarefaAtual
        global minInicioTarefaAtual
        tarefaAtual = filaTarefas[0]
        minInicioTarefaAtual = round(time.time())/60
        filaTarefas.pop(0)

        # Recupera dados da variante e objeto da tarefa
        info = obterInformacoesTarefa(tarefaAtual, variantes, plantas, canteiros)
        if info[0]: # Se a tarefa tem informações completas, interpreta as
                    # instruções da variante da tarefa
            global filaGCode
            filaGCode = interpretarInstrucoes(info[1], info[2])
            marcaTarefaProcessada(tarefaAtual['key'])
        else: # Se a tarefa não tem informações completas,
              # marca a falha no histórico
            marcaFalhaTarefa(tarefaAtual['key'], info[1])
    else: # Se a fila de tarefas estiver vazia
        logInfo(f"Fim da lista de tarefas")
        return False




if __name__ == "__main__":
    inicializarRobo()
    reestabelecerRobo()
    atualizarConhecimento()

    proximoReporteEstado = 0
    while True:
        # Registra a hora de inicio do loop principal
        agora = time.time()

        # Obtem o estado dos periféricos e a atividade do robô. E verifica se ha estado
        # de Alarme nos periféricos ou outra condicao que exija acao de recuperacao.
        estado = estadoRobo(GRBL, HEAD, PUMP, filaTarefas, tarefaAtual, filaGCode, dormindo)
        recuperar = False
        if estado['GRBL']['estado'] == "Alarm":
            # Um estado de Alarme do GRBL exige uma ação de destravamento.
            logWarning(f"GRBL em estado de alarme. Desativando alarme GRBL")
            desativaAlarme(GRBL)
            recuperar = True
        # Se foi realizada acao de recuperacao precisa atualizar o estado
        if recuperar: estado = estadoRobo(GRBL, HEAD, PUMP, filaTarefas, tarefaAtual, filaGCode, dormindo)

        # Verifica se ha alguma atividade em andamento. O robô está ativo
        # se algum dos periféricos não está em estado Idle. Se todos estiverem, ou
        # se nenhum periférico estiver instalado, ele está inativo
        ativo = False
        if GRBL and estado['GRBL']['estado'] == 'Run': ativo = True
        #TODO: manusear os estados dos demais perifericos
        #TODO: if HEAD and estado["HEAD"]["estado"] == "Run": ativo = True 
        #TODO: if PUMP and estado["PUMP"]["estado"] != "Idle": ativo = True 

        # Verifica se deve dormir
        # Se ha atividade em andamento,comandos na fila, ou reporte de
        # estado necessario, deve ficar acordado.
#        dormindo = not (ativo or len(filaGCode)>0)

        # Começa o loop principal após as verificações e recuperações
        logDebug(f"Loop principal iniciado. Ativo: {ativo}. Dormindo: {dormindo}")

        # Se for necessario, reporta o estado no RTD
        if agora > proximoReporteEstado: reportaEstadoRTD(estado)

        if dormindo:
        # Se estiver dormindo, quer dizer que nao ha comandos na fila
        # nem alguma atividade em andamento. O robo vai continuara doemindo
        # ate obter uma nova tarefa da fila. Isso acontece ou pelo decurso de
        # intervalo da consulta de tarefas ou por acao do listener da chave de
        # tarefas, que adianta a proxima consulta. De qualquer modo, isso
        # acontece quando agora > proxima Consulta.
            # Se necessário (por decurso de prazo e fila de tarefas vazia),
            # consulta a fila de tarefas e atualiza o registro do prazo da
            # próxima consulta de fila de tarefas
            if agora > proximaConsultaTarefas and not len(filaTarefas):
                filaTarefas = obterFilaTarefas()
                # TODO: considerar que o GRBL ou HEAD podem estar offline para finalidade de
                # busca da tarefa. Nesse caso, deveria processar o dicionário de ferramentas
                # disponíveis antes de fazer a busca pela fila
                proximaConsultaTarefas = agora + config['intervaloConsultaTarefas']
                
                if len(filaTarefas): # Se a consulta retornar alguma tarefa, otimiza
                                     # a fila de tarefas e acorda
                    filaTarefas = otimizarFilaTarefas()
                    dormindo = False
                    if not len(filaGCode): processarProximaTarefa()
                else:
                    # Se a consulta não retornar nenhuma tarefa, continua dormindo
                    dormindo = True

        else:
            # Se nao estiver dormindo, quer dizer que ha comandos na fila
            # ou alguma atividade em andamento. Independente do caso, deve
            # processar a fila de comandos, pois pode ser possível enviar
            # um novo comando.
            posFilaGCode = processaFilaGCode(filaGCode, GRBL, estado['GRBL']['lookahead_buffer'], HEAD, 99, PUMP, 99, tarefaAtual['key'], posFilaGCode)
            if posFilaGCode >= len(filaGCode):
                marcaTarefaConcluida(minInicioTarefaAtual)
                tarefaAtual = {}
                processarProximaTarefa()
            #TODO Implementar buffer de HEAD e PUMP

        # espera o intervalo de frequencia do loop principal.
        time.sleep(config['baixaFrequencia'] if dormindo else config['frequencia'])

# o processamento da fila espera:
            # - GRBL desconectado --> aguarda o próximo loop (espera reestabelecer conexão)
            # - GRBL em alarme    --> aguarda o próximo loop (espera destravar GRBL)
            # - buffer GRBL cheio --> aguarda o próximo loop (espera liberar buffer)
            # - HEAD desconectado --> aguarda o próximo loop (espera reestabelecer conexão)
