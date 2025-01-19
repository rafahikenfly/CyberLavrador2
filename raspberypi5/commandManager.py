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
    filaComandos[i]["resposta"] = resposta
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
            if GRBL: 
                resposta = enviaGCode(GRBL, instrucao)
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} GRBL <--{resposta}")
                if resposta[0]: processaSucessoComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
                else:           processaErroComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
                continue
            else:
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} GRBL desconectado")
                processaSucessoComando("GRBL desconectado", filaComandos, historicoComandos, 0, verbose)

        # Outros comandos  são enviados para o periférico de destino apenas se o GRBL estiver parado.
        # Isso acontece porque as operações de ferramenta devem iniciar apenas quando o GRBL estiver em posição,
        # o que acontece quando ele fica em estado "Idle". Caso o robô esteja muito lento, é possível implementar
        # um protocolo que verifica a posição do GRBL antes de enviar comandos para a ferramenta.
        # Se não estiver parado, sai do loop e tenta novamente na próxima iteração.
        elif instrucao.startswith("M"):
            if GRBL and HEAD:
                # Antes de se preocupar com o comando em si, precisa verificar se o GRBL está em posiçao.
                # Isso significa que ele está respondendo e com estado "Idle". Nesse caso, encerra o processamento
                # da fila de comandos, pois não sabemos quanto tempo vai levar para concluir a operação sendo realizada
                # pelo GRBL.
                resposta = enviaGCode(GRBL, "?")
                if not resposta[0] or resposta[1]["estado"] != "Idle": break

                # Primeiro verifica se o comando é suportado.
                # Se não for, registra o erro e passa para o próximo comando.
                if COMANDOS_SUPORTADOS[instrucao] == None:
                    processaErroComando ("Comando M desconhecido", filaComandos, historicoComandos, 0, verbose)
                    continue

                # Se o comando for suportado, envia para o destino e registra a resposta.
                periferico = COMANDOS_SUPORTADOS[instrucao]["periferico"]

            if periferico == "HEAD":
                # Comandos M12 e M13 para a HEAD são enviados apenas se ela estiver com a ferramenta correta montada.
                if instrucao == "M12" or instrucao == "M13":
                    processaSucessoComando("ok: não implementado", filaComandos, historicoComandos, 0, verbose)
                    #TODO implementar verificação de ferramenta
                    #resposta = enviaGCode(HEAD, instrucao)
                else:
                    verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} {periferico} -->{instrucao}")
                    if HEAD:
                        resposta = enviaGCode(HEAD, instrucao)
                        verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} {periferico} <--{resposta}")
                        if not resposta[0]: processaErroComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
                        else:               processaSucessoComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
                    else:
                        verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} HEAD desconectado")
                    
            elif periferico == "CAME":
                    processaSucessoComando("ok: não implementado", filaComandos, historicoComandos, 0, verbose)
                    #TODO implementar comandos de camera
                    #resposta = enviaGCode(CAME, instrucao)
            elif periferico == "PUMP":
                    processaSucessoComando("ok: não implementado", filaComandos, historicoComandos, 0, verbose)
                    #TODO implementar comandos de bombeamento
                    #resposta = enviaGCode(PUMP, instrucao)
            else:
                processaErroComando("Periférico desconhecido", filaComandos, historicoComandos, 0, verbose)
        # Se não começa com G ou com M, é um comando suportado, registra o erro e passa para o próximo comando.
        else:
            processaErroComando(f"Comando não suportado: {instrucao}", filaComandos, historicoComandos, 0, verbose)
