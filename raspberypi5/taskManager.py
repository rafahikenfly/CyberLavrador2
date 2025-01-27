import time
from firebase import push_realtime_db
from firebase import read_realtime_db
from firebase import update_realtime_db
from firebase import read_filtered_realtime_db

terrain = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/cartografia/"+ terrain + "/tarefas"

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
            ferramentas = dictManejos[tarefa["acao"]["manejoVinculado"]]["ferramenta"]
            
            disponivel = True
            for ferramenta, necessaria in ferramentas.items():
                if necessaria and not dictFerramental[ferramenta]["instalada"]:
                    disponivel = False
                    break
            if disponivel:
                viaveis[chave] = tarefa
        return viaveis
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
                    postergaTarefa(chave, round(time.time()*1000)+3600000, "Tarefa fora de horário permitido.") # TODO: no caso da hora, postergar para a primeira hora que permitida a tarefa
                    disponivel = False
                if condicaoForaDoLimite(300, condicoes["luminosidade"]):
                    print("Tarefa", chave, "não pode ser realizada com a luminosidade atual: 300.") #TODO definir como a condicao é obtida.
                    postergaTarefa(chave, round(time.time()*1000)+3600000, "Tarefa do intervalo de luminosidade permitido.") # TODO: no caso da hora, postergar para a primeira hora que permitida a tarefa
                    disponivel = False
                if condicaoForaDoLimite(30, condicoes["temperatura"]):
                    print("Tarefa", chave, "não pode ser realizada com a temperatura atual: 300.") #TODO definir como a condicao é obtida.
                    postergaTarefa(chave, round(time.time()*1000)+3600000, "Tarefa do intervalo de temperatura permitido.") # TODO: no caso da hora, postergar para a primeira hora que permitida a tarefa
                    disponivel = False
                if condicaoForaDoLimite(300, condicoes["umidade"]):
                    print("Tarefa", chave, "não pode ser realizada com a umidade de solo atual: 300.") #TODO definir como a condicao é obtida.
                    postergaTarefa(chave, round(time.time()*1000)+3600000, "Tarefa do intervalo de umidade permitido.") # TODO: no caso da hora, postergar para a primeira hora que permitida a tarefa
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

def obtemFila(dictManejos, tamanho = 100, dictFerramental = {}, verbose=False):
        try:
            #Busca a lista de tarefas, respeitando o lote de consulta
            #Apenas as tarefas com estado Aguardando interessam
            aguardando = read_filtered_realtime_db(pathTarefas, "estado", "Aguardando", tamanho)
            verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} {len(aguardando)} tarefa(s) com estado Aguardando no lote.")

            #Filtra aquelas que podem ser realizadas pelo robo com suas ferramentase pelas condições da classe, ordenando por prazo
            vencidas = filtrarVencidas(aguardando, round(time.time()*1000))
            verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} {len(vencidas)} tarefa(s) vencidas.")
            if len(vencidas) == 0: return []
            viaveis = filtrarViaveis(vencidas,dictManejos,dictFerramental)
            verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} {len(viaveis)} tarefa(s) que podem ser realizadas com meu ferramental.")
            if len(viaveis) == 0: return []
            oportunas = filtrarPorCondicao(viaveis,dictManejos)
            verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} {len(oportunas)} tarefa(s) em condição de execução.")
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
                comandos.append(instrucao[i])
            i = i + 1
    return (comandos)

def anotaTarefa(strChave, strAnotacao):
    push_realtime_db(pathTarefas + "/" + strChave + "/historico", {
        "autor": "Cyberlavrador 2.0",
        "hora": round(time.time()*1000),
        "anotacao": strAnotacao,
    })

def postergaTarefa(strChave, intNovaHora, motivo):
    update_realtime_db(pathTarefas + "/" + strChave + "/programa", {"prazo": intNovaHora})
    anotaTarefa(strChave, "Tarefa adiada para " + datetime.fromtimestamp(intNovaHora/1000).strftime("%H:%M:%S %d/%m/%y") + ": " + motivo)

def processaTarefa(strChave):
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "Processada"})
    anotaTarefa(strChave, "Tarefa processada pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y"))

def falhaTarefa(strChave, erro):
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "Falha"})
    anotaTarefa(strChave, "Tarefa falhou pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y") + ": " + erro)

def concluiTarefa(strChave):
    # Anota a conclusao da tarefa
    update_realtime_db(pathTarefas + "/" + strChave, {"estado": "Concluida"})
    anotaTarefa(strChave, "Tarefa concluida pelo CyberLavrador em " + time.strftime("%H:%M:%S %d/%m/%y"))
    
    # Caso a tarefa tenha repeticoes, replica a tarefa para o proximo intervalo
    tarefa = read_realtime_db(pathTarefas + "/" + strChave)
    if tarefa["programa"]["repeticoes"]:
        tarefa["programa"]["repeticoes"] = tarefa["programa"]["repeticoes"] - 1
        tarefa["programa"]["prazo"] = round(time.time()*1000) + 86400000 * tarefa["programa"]["intervalo"]
        tarefa["estado"] = "Aguardando"
        del tarefa["historico"]
        tarefa["key"] = push_realtime_db(pathTarefas,tarefa)
        update_realtime_db(pathTarefas + "/" + tarefa["key"], {"key": tarefa["key"]})
        anotaTarefa(tarefa["key"], "Repeticao de tarefa criada pelo CyberLavrador 2.0 em " + time.strftime("%H:%M:%S %d/%m/%y"))
