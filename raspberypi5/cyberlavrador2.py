from firebase import initialize_firebase
from firebase import read_realtime_db, update_realtime_db, listen_realtime_db, read_filtered_realtime_db
from comunicacao import conectaPorta
from grbl import desativaAlarme
from grbl import desativarMotores
from grbl import softReset

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

from gestorComandos import processaFilaGCode
from gestorComandos import recuperarComandos
from gestorComandos import salvarComandos
from gestorComandos import timeoutComando

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
    global GRBL
    global HEAD
    global PUMP
    # inicializa o robo, conectando o firebase com seus listeners
    # e conectando os perifericos


    initialize_firebase()

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
        logDebug(f"Tarefa atualizada: {event.path}")
        adiantarConsultaTarefas = False
        
        # no caso de um event.data que seja um dicionario,
        # verifica as propriedades
        if isinstance(event.data, dict):
            # verifica se deve acordar por mudanca no estado
            if 'estado' in event.data and event.data['estado'] == "aguardando":
                adiantarConsultaTarefas = True
            # verifica se deve acordar por mudanca no prazo
            if 'programa' in event.data and 'prazo' in event.data['programa']:
                prazo_timestamp = event.data['programa']['prazo']
                if prazo_timestamp < round(time.time() * 1000):
                    adiantarConsultaTarefas = True
                    
        # no caso de um event.data que seja um string
        # verifica o final do caminho
        elif event.path.endswith('/estado') and event.data == "aguardando":
            adiantarConsultaTarefas = True
        elif event.path.endswith('/prazo') and event.data < round(time.time() * 1000):
            adiantarConsultaTarefas = True
    
        # acorda, se for o caso
        if adiantarConsultaTarefas:
            proximaConsultaTarefas = 0
            logInfo("Consultando tarefas...")

    # Configura os listeners
    listen_realtime_db(pathConfiguracao, listenerConfig)
    listen_realtime_db(pathFerramenta, listenerFerramentas)
    listen_realtime_db(pathTarefas, listenerTarefas)

    #conecta com os perifericos
    GRBL = conectaPorta(config['GRBLPort'], config['GRBLBaud'], "GRBL")
    HEAD = conectaPorta(config['HEADPort'], config['HEADBaud'], "HEAD")
    PUMP = conectaPorta(config['PUMPPort'], config['PUMPBaud'], "PUMP")
    #TODO:TEST utilizar configurações dos periféricos registradas no firebase
#    HEAD = conectaPorta(HEADport, HEADbaudrate, "HEAD")
#    PUMP = conectaPorta(PUMPport, PUMPbaudrate, "PUMP")
#    GRBLport = "/dev/ttyACM0"
#    HEADport = "/dev/ttyUSB0"
#    PUMPport = "/dev/ttyACM2"
#    GRBLbaudrate = 115200  # Velocidade padrao do GRBL
#    HEADbaudrate = 9600
#    PUMPbaudrate = 9600


def reestabelecerRobo():
    global filaGCode
    global tarefaAtual
    global dormindo
    global minInicioTarefaAtual
    # Recupera a lista de comandos e a tarefa que estava sendo processada. Se ha uma lista
    # significa que houve um erro durante a execucao da tarefa.
    recover = recuperarComandos("comandos.pkl")
    if len(recover[0]):
        logInfo(f"Recuperados {len(recover[0])} comandos da execucao da tarefa {recover[1]}")
        # Tenta identificar a tarefa que teve problema e descobrir se ela ainda esta
        # com o estado de processada. No meio tempo, ela pode ter sido realizada, ou
        # ate mesmo apagada
        if 'key' in recover[1]:
            tarefaAtualizada = read_realtime_db(f"{pathTarefas}/{recover[1]['key']}")
            if tarefaAtualizada and tarefaAtualizada['estado'] == 'processada':
                filaGCode = recover[0]
                tarefaAtual = tarefaAtualizada
                if len(filaGCode):
                    dormindo = False
                    minInicioTarefaAtual = round(time.time())/60
            else:
                # se a tarefa nao foi identificada
                logInfo(f"Execucao da tarefa {recover[1]['key']} deprecada")
                filaGCode = []
                tarefaAtual = {}
                salvarComandos(filaGCode,tarefaAtual)

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
    global proximoReporteEstado
    global proximaConsultaTarefas
    logInfo("Enviado estado do robo para o RTD")
    logDebug(estado)
    update_realtime_db(pathDispositivo + "/estado", estado)
    proximoReporteEstado = (round(agora) + config['intervaloReporteEstadoInativo']) * 1000 if dormindo else (round(agora) + config['intervaloReporteEstadoAtivo']) * 1000
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
    global dormindo
    global filaGCode
    global tarefaAtual
    global minInicioTarefaAtual
    if len(filaTarefas): # Se a fila de tarefas não estiver vazia, recupera 
                         # a primeira tarefa da fila e registra o horário de
                         # início do processamento, para registrar o tempo
                         # de execução quando a tarefa for concluída
        tarefaAtual = filaTarefas[0]
        minInicioTarefaAtual = round(time.time())/60
        filaTarefas.pop(0)

        # Recupera dados da variante e objeto da tarefa
        info = obterInformacoesTarefa(tarefaAtual, variantes, plantas, canteiros)
        if info[0]: # Se a tarefa tem informações completas, interpreta as
                    # instruções da variante da tarefa
            filaGCode = interpretarInstrucoes(info[1], info[2])
            marcaTarefaProcessada(tarefaAtual['key'])
            salvarComandos(filaGCode, tarefaAtual)
        else: # Se a tarefa não tem informações completas,
              # marca a falha no histórico
            marcaFalhaTarefa(tarefaAtual['key'], info[1])
    else: # Se a fila de tarefas estiver vazia
        logInfo(f"Fim da lista de tarefas. Dormindo...")
        dormir()
        return False

def dormir():
    global dormindo
    dormindo = True
    desativarMotores()

    # TODO: quando dormir, desligar os motores e voltar para home

def acordar():
    global dormindo
    global filaGCode
    dormindo = False
    softReset()
    desativaAlarme()
    if not len(filaGCode): processarProximaTarefa()

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
        # se houver algum gcode na fila ou se algum dos periféricos não está em estado Idle.
        # Esta última condição é importante especialmente no caso de muitos comandos
        # enviados para o GRBL no final de uma tarefa
        ativo = False
        if len(filaGCode): ativo = True
        if GRBL and estado['GRBL']['estado'] == 'Run': ativo = True
        if HEAD and estado['HEAD']['estado'] == 'Run': ativo = True 
        #TODO: manusear os estados dos demais perifericos
        #TODO: if PUMP and estado["PUMP"]["estado"] != "Idle": ativo = True 

        # Começa o loop principal após as verificações e recuperações
        logDebug(f"Loop principal iniciado. Ativo: {ativo}. Dormindo: {dormindo}. Fila Tarefa: {len(filaTarefas)}. Fila GCode: {len(filaGCode)}")

        # Se for necessario, reporta o estado no RTD
        # TODO:TEST está enviando a cada loop o estado
        # TODO: durante o processamento da fila não atualiza o estado
        if agora > proximoReporteEstado: reportaEstadoRTD(estado)

        if dormindo:
        # Se estiver dormindo, quer dizer que nao ha comandos na fila,
        # nem movimento nos motores ou tarefas na fila. O robo vai continuara
        # dormindovate obter uma nova tarefa da fila, o que acontece decorrido o
        # intervalo da consulta de tarefas ou por acao do listener da chave de
        # tarefas, que adianta a proxima consulta. Ambas as situações são identificadas
        # por agora > proxima Consulta.
            # Se necessário (por prazo decorrido e fila de tarefas vazia),
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
                    acordar()
                else:
                    logDebug(f"Nenhuma nova tarefa, continuando a dormir.")

        else:
            # Se não está dormindo, ou há comandos na fila de gcodes ou há atividade
            # em andamento. Independente do caso, deve processar a fila de gcodes,
            # pois é provável que se possam enviar novos comandos. Processa um timeout
            # no caso de um comando que trave o robo por determinado tempo
            prevPosFilaGCode = posFilaGCode
            posFilaGCode = processaFilaGCode(filaGCode, GRBL, estado['GRBL']['lookahead_buffer'], HEAD, estado['GRBL']['lookahead_buffer'], PUMP, 99, tarefaAtual['key'], posFilaGCode)
            #TODO: Implementar buffer de PUMP
            #TODO:TEST Implementar buffer de HEAD            

            #TODO:TEST timeout no caso de muita espera de um comando da fila
            # O timeout do comando gera um erro na fila no caso de a posição anterior
            # ser igual a posicao nova mesmo após o tempo de timeout. Cada loop que
            # avanca na fila reestabelece o timer de timeout
            if prevPosFilaGCode != posFilaGCode:
                gCodeTimeout = agora + config['gcodeTimeout']
            elif agora > gCodeTimeout:
                timeoutComando(filaGCode, tarefaAtual['key'], posFilaGCode)
            #TODO:TEST so marcar tarefa como concluida com os periféricos em Idle
            if posFilaGCode >= len(filaGCode) and estado['GRBL']['estado'] == 'Idle':
                marcaTarefaConcluida(tarefaAtual['key'], minInicioTarefaAtual)
                filaGCode = []
                tarefaAtual = {}
                salvarComandos(filaGCode,tarefaAtual)
                processarProximaTarefa()

        # espera o intervalo de frequencia do loop principal.
        time.sleep(config['baixaFrequencia'] if dormindo else config['frequencia'])

# o processamento da fila espera:
            # - GRBL desconectado --> aguarda o próximo loop (espera reestabelecer conexão)
            # - GRBL em alarme    --> aguarda o próximo loop (espera destravar GRBL)
            # - buffer GRBL cheio --> aguarda o próximo loop (espera liberar buffer)
            # - HEAD desconectado --> aguarda o próximo loop (espera reestabelecer conexão)
