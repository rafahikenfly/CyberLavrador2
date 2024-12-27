import time
from firebase import push_realtime_db
from firebase import update_realtime_db

terrain = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/loteamento/"+ terrain + "/tarefas"

from datetime import datetime

# Funções de processamento da fila de tarefas
def filtrarPorHora(dictTarefas, hora):
    """
    Filtra um dicionário no formato {a: {hora: valor}} para incluir apenas
    os itens onde valor > 100.

    :param dictTarefas: O dicionário a ser filtrado.
    :param hora: a hora mínima para incluir no resultado.
    :return: dict: Um novo dicionário com os itens filtrados.
    """
    return {k: v for k, v in dictTarefas.items() if 'hora' in v and v['hora'] >= hora}
def filtrarPorAcessorios(dictTarefas, acessorios):
    """
    Filtra os itens de um dicionário de tarefas com base em uma lista de acessorios.

    :param dicionario: Dicionário a ser filtrado (formato {chave: {campo: valor}}).
    :param acessorios: Dicionário com os acessorios de filtragem ({campo: bool}).
    :return: Um novo dicionário contendo apenas os itens que podem ser atendidos com os acessorios.
    """
    return {
        k: v
        for k, v in dictTarefas.items()
        if isinstance(v, dict) and all(v.get(campo) == False or v.get(campo) == valor_procurado for campo, valor_procurado in acessorios.items())
    }

def tarefaForaDeParametro (intValor, dictCondicao):
    """
    Verifica se um parâmetro está fora da condição exigida.

    :param intValor: Valor de referência.
    :param dictCondicao: Dicionário com a condição exigida (formato {min: valor, max: valor})
    :return: boolean
    """
    if dictCondicao == None:
        return False
    min = dictCondicao.get("min")
    max = dictCondicao.get("max")
    return intValor < min or intValor > max

def filtrarPorCondicao(dictTarefas, BOK):
    """
    Filtra os itens de um dicionário de tarefas com base em um BOK disponível no RTD.

    :param dicionario: Dicionário a ser filtrado (formato {chave: {campo: valor}}).
    :param BOK: Dicionário com informações de classes de tarefa.
    :return: Uma lista com um dicionário contendo as tarefas que não estão disponíveis e as que estão disponíveis, a patir das condições exigidas.
    """
    tarefasDisponiveis = []
    tarefasIndisponiveis = []
    for chave, tarefa in dictTarefas.items():
        disponivel = True
        classe = BOK.get(tarefa.get("classe"))
        if tarefaForaDeParametro(time.localtime().tm_hour, classe.get("condicao").get("hora")): 
            print("Tarefa", chave, "não pode ser realizada no horário atual:", time.strftime("%H:%M:%S"), ".")
            postergaTarefa(chave, time.time()+3600, "Tarefa fora de horário permitido.")
            disponivel = False
        if tarefaForaDeParametro(300, classe.get("condicao").get("umidade")):
            print("Tarefa", chave, "não pode ser realizada com a umidade de solo atual: 300.") #TODO definir como a umidade é obtida.
            disponivel = False
        ## outras condições conhecidas vão aqui
        tarefa["chave"]=chave
        if disponivel: tarefasDisponiveis.append(tarefa)
        else: tarefasIndisponiveis.append(tarefa)
    return tarefasIndisponiveis, tarefasDisponiveis

def ordenarListaPorChave(lista, chave, reverso=False):
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
        return sorted(lista, key=lambda x: x[chave], reverse=reverso)
    except KeyError:
        raise KeyError(f"A chave '{chave}' não existe em algum dos dicionários fornecidos.")

# Funções de processamento de tarefas
def preparaComandos(classe, objeto):
    """
    Prepara os comandos de uma tarefa

    :param tarefa: Dicionário com a tarefa a ser realizada.
    :param classe: Dicionário com a classe da tarefa.
    :param objeto: Dicionário com o objeto alvo da tarefa.
    :return: Um novo dicionário contendo apenas as tarefas que podem ser realizadas com as condições exigidas.
    """
    comandos = []
    i = 0
    loopCount = 0
    loopTotal = 0
    loopGoto = 0
    instrucao = classe.get("instrucoes")
    while i < len(instrucao):
        if isinstance(instrucao[i], str):
            instrucao[i] = instrucao[i].replace("<Xmax>", "X" + str(objeto.get("posicao").get("X")))
            instrucao[i] = instrucao[i].replace("<Xmin>", "X" + str(objeto.get("posicao").get("X")))
            instrucao[i] = instrucao[i].replace("<Ymax>", "Y" + str(objeto.get("posicao").get("Y")))
            instrucao[i] = instrucao[i].replace("<Ymin>", "Y" + str(objeto.get("posicao").get("Y")))
            instrucao[i] = instrucao[i].replace("<Zmax>", "Z" + str(objeto.get("posicao").get("z")))
            instrucao[i] = instrucao[i].replace("<Zmin>", "Z" + str(objeto.get("posicao").get("X")))
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
    push_realtime_db(pathTarefas + "/" + strChave + "/historico", strAnotacao)

def postergaTarefa(strChave, intNovaHora, motivo):
    update_realtime_db(pathTarefas + "/" + strChave, {"hora": intNovaHora})
    anotaTarefa(strChave, "Tarefa adiada para " + datetime.fromtimestamp(intNovaHora).strftime("%H:%M:%S %d/%m/%y") + ": " + motivo)

def processaTarefa(strChave):
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "processada"})
    anotaTarefa(strChave, "Tarefa processada pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y"))

def falhaTarefa(strChave):
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "falha"})
    anotaTarefa(strChave, "Tarefa falhou pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y"))

def concluiTarefa(strChave):
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "concluida"})
    anotaTarefa(strChave, "Tarefa concluida pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y"))

