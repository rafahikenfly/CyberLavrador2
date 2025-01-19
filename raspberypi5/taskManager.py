import time
from firebase import push_realtime_db
from firebase import update_realtime_db
from firebase import read_filtered_realtime_db
from config import QUEUE
from config import FERRAMENTAS
terrain = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/cartografia/"+ terrain + "/tarefas"

from datetime import datetime

# Funções de processamento da fila de tarefas
def filtrarPrazo(dictTarefas, prazo):
    """
    Filtra um dicionário no formato {a: {prazo: valor}} para incluir apenas
    os itens onde valor > prazo estabelecido.

    :param dictTarefas: O dicionário a ser filtrado.
    :param prazo: o prazo mínimo para incluir no resultado.
    :return: dict: Um novo dicionário com os itens filtrados.
    """
    return {k: v for k, v in dictTarefas.items() if v['programa']['prazo'] >= prazo}
def filtrarFerramental(dictTarefas, dictManejos, dictFerramental):
    """
    Filtra os itens de um dicionário de tarefas com base em uma lista de acessorios.

    :param dicionario: Dicionário a ser filtrado (formato {chave: {campo: valor}}).
    :param manejos: Dicionário com informacoes das manejos (formato {chave: {campo: valor}}).
    :param acessorios: Dicionário com os acessorios de filtragem ({campo: bool}).
    :return: Um novo dicionário contendo apenas os itens que podem ser atendidos com os acessorios.
    """
    try:
        tarefasDisponiveis = {}
        for chave, tarefa in dictTarefas.items():
            ferramentas = dictManejos[tarefa["acao"]["manejoVinculado"]]["ferramenta"]
            
            disponivel = True
            for ferramenta, necessaria in ferramentas.items():
                if necessaria and not dictFerramental[ferramenta]["instalada"]:
                    disponivel = False
                    break
            if disponivel:
                tarefasDisponiveis[chave] = tarefa
        return tarefasDisponiveis
    except Exception as e:
        print(f"Erro ao filtrar ferramentas: {e}")
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
            condicoes = dictManejos[tarefa["acao"]["manejoVinculado"]]["condicao"]
            disponivel = True
            if not tarefa["acao"]["forcar"]:
                if condicaoForaDoLimite(time.localtime().tm_hour, condicoes["hora"]): 
                    print("Tarefa", chave, "não pode ser realizada no horário atual:", time.strftime("%H:%M:%S"), ".")
                    postergaTarefa(chave, time.time()+3600, "Tarefa fora de horário permitido.")
                    disponivel = False
                if condicaoForaDoLimite(300, condicoes["luminosidade"]):
                    print("Tarefa", chave, "não pode ser realizada com a luminosidade atual: 300.") #TODO definir como a condicao é obtida.
                    disponivel = False
                if condicaoForaDoLimite(300, condicoes["temperatura"]):
                    print("Tarefa", chave, "não pode ser realizada com a temperatura atual: 300.") #TODO definir como a condicao é obtida.
                    disponivel = False
                if condicaoForaDoLimite(300, condicoes["umidade"]):
                    print("Tarefa", chave, "não pode ser realizada com a umidade de solo atual: 300.") #TODO definir como a condicao é obtida.
                    disponivel = False
                ## outras condições conhecidas vão aqui
            tarefa["chave"] = chave
            if disponivel: tarefasDisponiveis.append(tarefa)
        return tarefasDisponiveis
    except Exception as e:
        print(f"Erro ao filtrar condição: {e}")
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

def obtemFila(dictClasses, verbose=False):
        try:
            #Busca a lista de tarefas, respeitando o lote de consulta
            #Apenas as tarefas com estado Aguardando interessam
            tarefasAguardando = read_filtered_realtime_db(pathTarefas, "estado", "Aguardando", QUEUE["loteConsulta"])
            verbose and print("Há", len(tarefasAguardando), "tarefa(s) aguardando realização.")

            #Filtra aquelas que podem ser realizadas pelo robo com suas ferramentase pelas condições da classe, ordenando por prazo
            vencidas = filtrarPrazo(tarefasAguardando,time.time())
            if len(vencidas) == 0: return []
            instrumentadas = filtrarFerramental(vencidas,dictClasses,FERRAMENTAS)
            verbose and print("Encontrei", len(instrumentadas), "tarefa(s) vencidas que sou capaz de realizar.")
            if len(instrumentadas) == 0: return []
            oportunas = filtrarPorCondicao(instrumentadas,dictClasses)
            verbose and print("Há", len(oportunas), "tarefa(s) disponíveis para realização.")
            listaTarefas = ordenarListaPorChave(oportunas,"programa","prazo")
            return listaTarefas
        except Exception as e:
            print(f"Erro ao obter fila de tarefas: {e}")
            return []

# Funções de processamento de tarefas
def preparaComandos(variante, objeto):
    """
    Prepara os comandos de uma tarefa

    :param tarefa: Dicionário com a tarefa a ser realizada.
    :param variante: Dicionário com a variante vinculada da tarefa.
    :param objeto: Dicionário com o objeto alvo da tarefa.
    :return: Um novo dicionário contendo apenas as tarefas que podem ser realizadas com as condições exigidas.
    """
    comandos = []
    i = 0
    loopCount = 0
    loopTotal = 0
    loopGoto = 0
    instrucao = variante.get("instrucoes")
    while i < len(instrucao):
        if isinstance(instrucao[i], str):
            instrucao[i] = instrucao[i].replace("<Xmax>", "X" + str(objeto["posicao"]["X"]+objeto["dimensao"]["X"]))
            instrucao[i] = instrucao[i].replace("<Xmin>", "X" + str(objeto["posicao"]["X"]))
            instrucao[i] = instrucao[i].replace("<Ymax>", "Y" + str(objeto["posicao"]["Y"]+objeto["dimensao"]["Y"]))
            instrucao[i] = instrucao[i].replace("<Ymin>", "Y" + str(objeto["posicao"]["Y"]))
            instrucao[i] = instrucao[i].replace("<Zmax>", "Z" + str(objeto["posicao"]["Z"]+objeto["dimensao"]["Z"]))
            instrucao[i] = instrucao[i].replace("<Zmin>", "Z" + str(objeto["posicao"]["X"]))
            instrucao[i] = instrucao[i].replace("<Xdim>", "Z" + str(objeto["dimensao"]["X"]))
            instrucao[i] = instrucao[i].replace("<Ydim>", "Z" + str(objeto["dimensao"]["Y"]))
            instrucao[i] = instrucao[i].replace("<Zdim>", "Z" + str(objeto["dimensao"]["Z"]))
            if instrucao[i].startswith("LOOP"):
                loopDefinition = instrucao[i].split(" ")
                loopTotal = int(loopDefinition[1])
                loopGoto = int(loopDefinition[2]) - 1
                if loopCount < loopTotal:
                    i = loopGoto
                    loopCount = loopCount + 1
            else:
                comandos.append(instrucao[i])
            i = i + 1
    return (comandos)

def anotaTarefa(strChave, strAnotacao):
    push_realtime_db(pathTarefas + "/" + strChave + "/historico", {
        "autor": "Cyberlavrador 2.0",
        "hora": time.time(),
        "anotacao": strAnotacao,
    })

def postergaTarefa(strChave, intNovaHora, motivo):
    update_realtime_db(pathTarefas + "/" + strChave, {"hora": intNovaHora})
    anotaTarefa(strChave, "Tarefa adiada para " + datetime.fromtimestamp(intNovaHora).strftime("%H:%M:%S %d/%m/%y") + ": " + motivo)

def processaTarefa(strChave):
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "Processada"})
    anotaTarefa(strChave, "Tarefa processada pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y"))

def falhaTarefa(strChave):
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "Falha"})
    anotaTarefa(strChave, "Tarefa falhou pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y"))

def concluiTarefa(strChave):
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "Concluida"})
    anotaTarefa(strChave, "Tarefa concluida pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y"))

