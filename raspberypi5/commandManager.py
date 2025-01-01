from grbl import enviaGCode
from taskManager import falhaTarefa
from taskManager import concluiTarefa
from config import COMANDOS_SUPORTADOS
import time

def processaErroComando(erro, filaComandos = [], historicoComandos = [], i = 0, verbose = False):
    """
    Processa um erro de comando, pulando para a próxima tarefa da fila (se existente) e registrando a falha.
    :param erro: string com a descrição do erro
    :param i: índice do comando que falhou
    :param filaComandos: lista de comandos a serem processados
    :param historicoComandos: lista de comandos já processados
    :param verbose: flag para exibir mensagens de debug
    """
    # Salva os dados do erro
    tarefaErro = filaComandos[i]["tarefa"]
    
    # Reporta erro na fila, debug e banco de dados
    filaComandos[i]["estado"] = "Erro"
    filaComandos[i]["resposta"] = erro
    verbose and print(f"Erro na execução da tarefa {tarefaErro}: : {erro}")
    falhaTarefa(tarefaErro)

    # Move comando para histórico
    avancaFila(i, filaComandos, historicoComandos)

    # Cancela comandos da tarefa
    while filaComandos[i]["tarefa"] == tarefaErro:
        if i + 1 == len(filaComandos): break # Se for o último comando, sai do loop
        verbose and print(f"Pulando comando {filaComandos[i]} por falha na tarefa relacionada.")
        filaComandos[i]["resposta"] = "Falha na tarefa relacionada."
        filaComandos[i]["estado"] = "Cancelado"
        avancaFila(i, filaComandos, historicoComandos)
    return filaComandos, historicoComandos

def processaSucessoComando(resposta, filaComandos = [], historicoComandos = [], i = 0, verbose = False):
    """
    Processa um sucesso de comando, registrando a conclusão da tarefa.
    :param filaComandos: lista de comandos a serem processados
    :param i: índice do comando que falhou
    :param verbose: flag para exibir mensagens de debug
    :return Null
    """
    
    #Reporta conclusão na fila
    filaComandos[1]["resposta"] = resposta
    filaComandos[i]["estado"] = "Concluido"
    tarefa = filaComandos[i]["tarefa"]
    
    # Se for o último comando da tarefa, registra a conclusão
    if i == len(filaComandos) - 1 or filaComandos[i+1]["tarefa"] != tarefa:
        verbose and print(f"Tarefa {tarefa} executada.")
        concluiTarefa(tarefa)
    avancaFila(i, filaComandos, historicoComandos)
    return filaComandos, historicoComandos

def avancaFila(i, filaComandos, historicoComandos):
    """
    Avança a fila de comandos para a próxima tarefa.
    :param i: índice do comando que falhou
    :param filaComandos: lista de comandos a serem processados
    :param historicoComandos: lista de comandos já processados
    :param verbose: flag para exibir mensagens de debug
    """
    historicoComandos.append(filaComandos[i])
    filaComandos.pop(i)
    return filaComandos, historicoComandos

def processaFilaComandos(GRBL, HEAD, PUMP, filaComandos = [], historicoComandos = [], verbose = False):
    while True:
        # Verifica se há comandos na fila. Se não há comandos na fila, sai do loop.
        if len(filaComandos) == 0: break

        comando = filaComandos[0]
        instrucao = comando["instrucao"]

        # Comandos G vão sempre ser enviados para o GRBL
        # Está implementado um protocolo simples de Send-Response. Por isso não é preciso verificar se
        # o GRBL está disponível para receber comandos. Caso o robô esteja muito lento, é possível
        # implementar um protocolo que utiliza o buffer serial do GRBL.
        if instrucao.startswith("G"):
            verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} GRBL -->{instrucao}")
            resposta = enviaGCode(GRBL, instrucao)
            verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} GRBL <--{resposta[1]}")
            if resposta[0]: processaSucessoComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
            else:           processaErroComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
            continue
        
        # Outros comandos  são enviados para o periférico de destino apenas se o GRBL estiver parado.
        # Isso acontece porque as operações de ferramenta devem iniciar apenas quando o GRBL estiver em posição,
        # o que acontece quando ele fica em estado "Idle". Caso o robô esteja muito lento, é possível implementar
        # um protocolo que verifica a posição do GRBL antes de enviar comandos para a ferramenta.
        # Se não estiver parado, sai do loop e tenta novamente na próxima iteração.
        resposta = enviaGCode(GRBL, "?")
        if not resposta[0] or resposta[1]["estado"] != "Idle": break

        # Todos os demais comandos são strings de cinco letras.
        # 
        # Primeiro verifica se o comando é suportado.
        # Se não for, registra o erro e passa para o próximo comando.
        if COMANDOS_SUPORTADOS[instrucao] == None:
            processaErroComando ("Instrução desconhecida", filaComandos, historicoComandos, 0, verbose)
            continue
        
        # Se o comando for suportado, envia para o destino e registra a resposta.
        periferico = COMANDOS_SUPORTADOS[instrucao][periferico]
        verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} {periferico} -->{instrucao}")

        # Comandos para a HEAD são enviados apenas se ela estiver disponível e com a ferramenta em posição.
        # Se não estiver parado, sai do loop e tenta novamente na próxima iteração.
        if periferico == "HEAD":
            resposta = enviaGCode(HEAD, "?")
            if not resposta[0] or resposta[1]["estado"] != "Idle": break
            # TODO: Pode estar parada e com a ferramenta errada. Nesse caso, deve haver uma rotina de troca de ferramenta.
            comando["resposta"] = "ok" #TODO: implementar head enviaGCode(HEAD, interpretaHCode(instrucao))

        # Não está implementada a verificação de estado do destino de câmera e válvula. A premissa é que não é 
        # necessário verificar o estado do destino, pois todos os comandos são do tipo real-time.
        elif periferico == "CAME":
            comando["resposta"] = "ok" #TODO implementar câmera
        elif periferico == "PUMP":
            comando["resposta"] = "ok" #TODO implementar bomba enviaGCode(PUMP, interpretaHCode(instrucao))
        
        verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} {periferico} <--{comando['resposta']}")
        if resposta == "ok": processaSucessoComando(filaComandos, historicoComandos, 0, verbose)
        else: processaErroComando(comando["resposta"], filaComandos, historicoComandos, 0, verbose)
