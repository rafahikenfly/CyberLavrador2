import time
from firebase import push_realtime_db
from firebase import read_realtime_db
from firebase import update_realtime_db
from firebase import read_filtered_realtime_db

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning



terreno = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/tarefas/" + terreno
pathHistorico = "/anotacoes/" + terreno
pathRegistros = "/ registros/" + terreno

from datetime import datetime

# Funções de processamento da fila de tarefas
def filtrarVencidas(dictTarefas, prazo):
    """
    Filtra um dicionário de tarefas (no formato {programa: {prazo: valor}})
    para incluir apenas os itens onde valor e maior que um prazo estabelecido.

    :param dictTarefas: Dicionário a ser filtrado.
    :param prazo: o prazo mínimo para incluir no resultado.
    :return: dict: dicionário com as tarefas vencidas.
    """
    return {k: v for k, v in dictTarefas.items() if v['programa']['prazo'] <= prazo}
def filtrarViaveis(dictTarefas, dictManejos, dictFerramental):
    """
    Filtra um dicionário de tarefas (no formato {acao: {manejoVinculado})
    para incluir apenas aquelas cujas ferramentas estejam disponiveis.

    :param dicionario: Dicionário a ser filtrado.
    :param manejos: Dicionário com informacoes dos manejos (formato {chave: {ferramenta{ {ferramenta}: boolean}}}).
    :param acessorios: Dicionário com os acessorios de filtragem ({ferramenta: { {ferramenta}: bool}}).
    :return: dicionário com as tarefas viaveis.
    """
    try:
        viaveis = {}
        for chave, tarefa in dictTarefas.items():
            ferramentas = dictManejos[tarefa['acao']['manejoVinculado']]['ferramenta']
            
            disponivel = True
            for ferramenta, necessaria in ferramentas.items():
                if necessaria and not dictFerramental[ferramenta]['instalada']:
                    disponivel = False
                    break
            if disponivel:
                viaveis[chave] = tarefa
        return viaveis
    except Exception as e:
        logError(f"Erro ao filtrar tarefas viaveis com ferramentas disponiveis: {e}")
    return []


def condicaoForaDoLimite (intValor, dictCondicao):
    """
    Verifica se um parâmetro está fora da condição exigida.

    :param intValor: Valor de referência.
    :param dictCondicao: Dicionário com a condição exigida (formato {min: valor, max: valor})
    :return: boolean
    """
    if dictCondicao == None:
        return False
    min = dictCondicao["min"]
    max = dictCondicao["max"]
    return intValor < min or intValor > max

def filtrarPorCondicao(dictTarefas, dictManejos):
    """
    Filtra os itens de um dicionário de tarefas com base em um dicionário de manejos.

    :param dicionario: Dicionário a ser filtrado (formato {chave: {campo: valor}}).
    :param manejos: Dicionário com informacoes das manejos (formato {chave: {campo: valor}}).
    :return: um dicionário contendo as tarefas que não estão disponíveis, a patir das condições exigidas.
    """
    try:
        tarefasDisponiveis = []
        for chave, tarefa in dictTarefas.items():
            condicoes = dictManejos[tarefa["acao"]["manejoVinculado"]]["condicoes"]
            disponivel = True
            if not tarefa['acao']['forcar']:
                if condicaoForaDoLimite(time.localtime().tm_hour, condicoes["hora"]): 
                    logInfo(f"Tarefa {chave} não pode ser realizada no horário atual: {time.strftime('%H:%M:%S')}.")
                    postergaTarefa(chave, round(time.time()*1000) + 3600000, "Tarefa fora de horário permitido.") # TODO: no caso da hora, postergar para a primeira hora que permitida a tarefa
                    disponivel = False
                if condicaoForaDoLimite(300, condicoes['luminosidade']):
                    logInfo(f"Tarefa {chave} não pode ser realizada com luminosidade atual: {300}.") #TODO definir como a condicao é obtida.
                    postergaTarefa(chave, round(time.time()*1000) + 3600000, "Tarefa fora do intervalo de luminosidade permitido.")
                    disponivel = False
                if condicaoForaDoLimite(30, condicoes['temperatura']):
                    logInfo(f"Tarefa {chave} não pode ser realizada com temperatura atual: {30}.") #TODO definir como a condicao é obtida.
                    postergaTarefa(chave, round(time.time()*1000) + 3600000, "Tarefa fora do intervalo de temperatura permitido.")
                    disponivel = False
                if condicaoForaDoLimite(300, condicoes['umidadeSolo']):
                    logInfo(f"Tarefa {chave} não pode ser realizada com umidade de solo atual: {300}.") #TODO definir como a condicao é obtida.
                    postergaTarefa(chave, round(time.time()*1000) + 3600000, "Tarefa fora do intervalo de umidade permitido.") # TODO: no caso da hora, postergar para a primeira hora que permitida a tarefa
                    disponivel = False
                if condicaoForaDoLimite(50, condicoes['umidadeAr']):
                    logInfo(f"Tarefa {chave} não pode ser realizada no horário atual: {50}%.") #TODO definir como a condicao é obtida.
                    postergaTarefa(chave, round(time.time()*1000) + 3600000, "Tarefa fora do intervalo de umidade permitido.") # TODO: no caso da hora, postergar para a primeira hora que permitida a tarefa
                    disponivel = False
                ## outras condições conhecidas vão aqui
            tarefa["chave"] = chave
            if disponivel: tarefasDisponiveis.append(tarefa)
        return tarefasDisponiveis
    except Exception as e:
        logError(f"Erro ao filtrar tarefas por condição: {e}")
    return []


def ordenarListaPorChave(lista, chave, subchave, reverso=False):
    """
    Ordena uma lista de dicionários pelo valor de uma chave específica.
    
    Parâmetros:
        lista_dicionarios (list): Lista de dicionários para ordenar.
        chave (str): Chave pelo qual os dicionários serão ordenados.
        reverso (bool): Define se a ordem será decrescente. Padrão é False.
        
    Retorna:
        list: Lista de dicionários ordenada.
    """


    if not isinstance(lista, list):
        raise ValueError("O input deve ser uma lista de dicionários.")
    
    try:
        return sorted(lista, key=lambda x: x[chave][subchave], reverse=reverso)
    except KeyError:
        raise KeyError(f"A chave '{chave}' não existe em algum dos dicionários fornecidos.")

def obterFilaTarefas(dictManejos, tamanho = 100, dictFerramental = {}):
        try:
            #Busca a lista de tarefas, respeitando o lote de consulta
            #Apenas as tarefas com estado Aguardando interessam
            aguardando = read_filtered_realtime_db(pathTarefas, "estado", "aguardando", tamanho)
            logDebug(f"{len(aguardando)} tarefa(s) com estado Aguardando no lote.")

            #Filtra aquelas que podem ser realizadas pelo robo com suas ferramentase pelas condições da classe, ordenando por prazo
            vencidas = filtrarVencidas(aguardando, round(time.time()*1000))
            logDebug(f"{len(vencidas)} tarefa(s) vencidas.")
            if len(vencidas) == 0: return []
            viaveis = filtrarViaveis(vencidas,dictManejos,dictFerramental)
            logDebug(f"{len(viaveis)} tarefa(s) que podem ser realizadas com meu ferramental.")
            if len(viaveis) == 0: return []
            oportunas = filtrarPorCondicao(viaveis,dictManejos)
            logInfo(f"{len(oportunas)} tarefa(s) em condição de execução.")
            return oportunas
        except Exception as e:
            logError(f"Erro ao obter fila de tarefas: {e}")
            return []

def otimizaFilaTarefas(listaTarefas, bufferSize = 5):
    return ordenarListaPorChave(listaTarefas[:bufferSize],"programa","prazo")

def obterInformacoesTarefa (tarefa, variantes, plantas, canteiros):
    """
    Obtem as informações necessárias para o processamento da tarefa

    :param dict tarefa: dicionário com a tarefa
    :param dict variantes: dicionário das variantes de manejo
    :param dict plantas: dicionário das plantas do terreno
    :param dict canteiros: dicionário dos canteiros do terreno

    :return list: [True, dict Variante, dict Objeto] ou [False, str erro]
    """
    # Obtém a variante da tarefa, caso exista.
    varianteTarefa = None
    try:
        varianteTarefa = variantes[tarefa['acao']['manejoVinculado']][tarefa['acao']['varianteVinculada']]
    except KeyError:
        logError(f"Variante vinculada não encontrada para a tarefa: {tarefa['acao']['varianteVinculada']}")
        return False, f"Variante vinculada {tarefa['acao']['varianteVinculada']} não encontrada."
    
    # Obtém o objeto da tarefa, caso exista
    objetoTarefa = None
    objetoTipo = tarefa['objeto']['tipo']
    objetoChave = tarefa['objeto']['chave']
    
    if objetoTipo == "planta":
        try: objetoTarefa = plantas[objetoChave]
        except KeyError:
            logError(f"Planta vinculada a tarefa {tarefa['key']} não encontrada: {objetoChave}")
            return False, f"Planta vinculada {objetoChave} não encontrada."
    elif objetoTipo == "canteiro":
        try: objetoTarefa = canteiros[objetoChave]
        except KeyError:
            logError(f"Canteiro vinculado a tarefa {tarefa['key']} não encontrado: {objetoChave}")
            return False, f"Canteiro vinculado {objetoChave} não encontrado."
    else:
        logError(f"Tipo de objeto desconhecido: {objetoTipo}")
        return False, f"Tipo de objeto {objetoTipo} desconhecido."

    return True, varianteTarefa, objetoTarefa

# Funções de processamento de tarefas
def interpretarInstrucoes(variante, objeto):
    """
    Prepara os comandos de uma tarefa

    :param variante: Dicionário com a variante vinculada da tarefa.
    :param objeto: Dicionário com o objeto alvo da tarefa.
    :return: Um dicionário contendo gcodes processados.
    """
    esteiraGCode = []
    i = 0
    loopCount = 0
    loopTotal = 0
    loopStep = 0
    loopGoto = 0
    instrucao = variante.get("instrucoes")
    while i < len(instrucao):
        if isinstance(instrucao[i], str):
            instrucao[i] = instrucao[i].replace("<Xmax>", "X" + str(objeto["posicao"]["X"]+objeto["dimensao"]["X"]))
            instrucao[i] = instrucao[i].replace("<Xmin>", "X" + str(objeto["posicao"]["X"]))
            instrucao[i] = instrucao[i].replace("<Xcen>", "X" + str(objeto["posicao"]["X"]+objeto["dimensao"]["X"]/2))
            instrucao[i] = instrucao[i].replace("<Ymax>", "Y" + str(objeto["posicao"]["Y"]+objeto["dimensao"]["Y"]))
            instrucao[i] = instrucao[i].replace("<Ymin>", "Y" + str(objeto["posicao"]["Y"]))
            instrucao[i] = instrucao[i].replace("<Ycen>", "Y" + str(objeto["posicao"]["Y"]+objeto["dimensao"]["Y"]/2))
            instrucao[i] = instrucao[i].replace("<Zmax>", "Z" + str(objeto["posicao"]["Z"]+objeto["dimensao"]["Z"]))
            instrucao[i] = instrucao[i].replace("<Zmin>", "Z" + str(objeto["posicao"]["Z"]))
            instrucao[i] = instrucao[i].replace("<Zcen>", "Z" + str(objeto["posicao"]["Z"]+objeto["dimensao"]["Z"]/2))
            instrucao[i] = instrucao[i].replace("<Xdim>", "X" + str(objeto["dimensao"]["X"]))
            instrucao[i] = instrucao[i].replace("<Ydim>", "Y" + str(objeto["dimensao"]["Y"]))
            instrucao[i] = instrucao[i].replace("<Zdim>", "Z" + str(objeto["dimensao"]["Z"]))
            instrucao[i] = instrucao[i].replace("<Xdimval>", str(objeto["dimensao"]["X"]))
            instrucao[i] = instrucao[i].replace("<Ydimval>", str(objeto["dimensao"]["Y"]))
            instrucao[i] = instrucao[i].replace("<Zdimval>", str(objeto["dimensao"]["Z"]))
            if instrucao[i].startswith("LOOP"):
                loopDefinition = instrucao[i].split(" ")
                loopGoto  = int(loopDefinition[1])
                loopTotal = int(loopDefinition[2])
                loopStep  = int(loopDefinition[3] or 1)
                if loopCount < loopTotal:
                    i = loopGoto - 1 #o loop volta para o indice anterior, pois no final do loop passa para a proxima instrucao
                    loopCount = loopCount + loopStep
            else:
                esteiraGCode.append(instrucao[i])
            i = i + 1
    return (esteiraGCode)

def anotarHistoricoTarefa(strChave, strAnotacao):
    push_realtime_db(f"{pathHistorico}/{strChave}", {
        "autor": "Cyberlavrador 2.0",
        "carimboHora": round(time.time()*1000),
        "anotacao": strAnotacao,
    })
def registrar(strChave, parametro, valor):
    push_realtime_db(f"{pathRegistros}/{strChave}", {
        "parametro": parametro,
        "carimboHora": round(time.time()*1000),
        "valor": valor,
    })

def postergaTarefa(strChave, intNovaHora, motivo):
    update_realtime_db(f"pathTarefas/{strChave}/programa", {'prazo': intNovaHora})
    anotarHistoricoTarefa(strChave, f"Tarefa adiada para {datetime.fromtimestamp(intNovaHora/1000).strftime('%H:%M:%S %d/%m/%y')}: {motivo}")

def marcaTarefaProcessada(strChave):
    update_realtime_db(f"{pathTarefas}/{strChave}", {'estado': 'processada'})
    anotarHistoricoTarefa(strChave, f"Tarefa processada pelo CyberLavrador em {time.strftime('%H:%M:%S %d/%m/%y')}")

def marcaFalhaTarefa(strChave, erro):
    update_realtime_db(f"{pathTarefas}/{strChave}", {'estado': 'falha'})
    anotarHistoricoTarefa(strChave, f"Tarefa falhou pelo CyberLavrador em {time.strftime('%H:%M:%S %d/%m/%y')}: {erro}")

def marcaTarefaConcluida(strChave, horaInicio):
    # Anota a conclusao da tarefa
    update_realtime_db(f"{pathTarefas}/{strChave}", {'estado': 'concluida'})
    anotarHistoricoTarefa(strChave, f"Tarefa concluida pelo CyberLavrador em {time.strftime('%H:%M:%S %d/%m/%y')}")
    
    # Caso a tarefa tenha repeticoes, replica a tarefa para o proximo intervalo
    tarefa = read_realtime_db(f"{pathTarefas}/{strChave}")
    if tarefa['programa']['repeticoes']:
        tarefa['programa']['repeticoes'] = tarefa['programa']['repeticoes'] - 1
        tarefa['programa']['prazo'] = round(time.time()*1000) + 86400000 * tarefa['programa']['intervalo']
        tarefa['estado'] = 'aguardando'
        push_realtime_db(pathTarefas, tarefa)
        anotarHistoricoTarefa(tarefa['key'], f"Repeticao de tarefa criada pelo CyberLavrador 2.0 em {time.strftime('%H:%M:%S %d/%m/%y')}")
