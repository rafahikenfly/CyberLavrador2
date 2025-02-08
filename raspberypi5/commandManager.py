from comunicacao import enviaGCode
from grbl import obterEstadoGRBL
from taskManager import marcaFalhaTarefa
from taskManager import marcaTarefaConcluida
from config import COMANDOS_SUPORTADOS
import time
import pickle
import cv2
import os

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning

def processaErroGCode(erro, filaGCode, historicoGCode, i = 0):
    """
    Processa um erro de comando, pulando para a próxima tarefa da fila (se existente) e registrando a falha.
    
    :param string erro: string com a descrição do erro
    :param array filaGCode: lista de comandos a serem processados
    :param array historicoGCode: lista de comandos já processados
    :param int i=0: índice do comando que falhou
    """
    # Salva os dados do erro
    tarefaErro = filaGCode[i]["tarefa"]
    
    # Reporta erro na fila, debug e banco de dados
    filaGCode[i]["estado"] = "Erro"
    filaGCode[i]["resposta"] = erro
    logError(f"Erro na execução da tarefa {tarefaErro}, executando {filaGCode[i]['instrucao']}: {erro}")
    marcaFalhaTarefa(tarefaErro, erro)

    # Move comando para histórico
    avancaFila(i, filaGCode, historicoGCode)

    # Cancela comandos da tarefa
    while i<len(filaGCode) and filaGCode[i]["tarefa"] == tarefaErro:
        logDebug(f"Cancelando comando {filaGCode[i]} por falha na tarefa relacionada.")
        filaGCode[i]["resposta"] = "Cancelado por falha na tarefa relacionada."
        avancaFila(i, filaGCode, historicoGCode)
    return filaGCode, historicoGCode

def processaSucessoGCode(resposta, filaGCode, historicoGCode, i = 0):
    """
    Processa um sucesso de comando, registrando a conclusão da tarefa.
    :param filaGCode: lista de comandos a serem processados
    :param historicoGCode: lista de comandos já processados
    :param int i=0: índice do comando que falhou
    :return Null
    """
    
    #Reporta conclusão na fila de comandos
    filaGCode[i]["resposta"] = resposta
    
    # Se for o último comando da tarefa, registra a conclusão
    tarefa = filaGCode[i]["tarefa"]
    if i == len(filaGCode) - 1 or filaGCode[i+1]["tarefa"] != tarefa:
        logInfo(f"Tarefa {tarefa} concluida.")
        marcaTarefaConcluida(tarefa)
    avancaFila(i, filaGCode, historicoGCode)
    return filaGCode, historicoGCode

def processaEnvioGCode(ser, periferico, gcode, filaGCode, i=0):
    logDebug(f"{periferico} -->{parsedGCode[1]['gcode']}")
    filaGCode[i]['envio'] = round(time.time())*1000
    resposta = enviaGCode(ser, parsedGCode[1]['gcode'])
    logDebug(f"{periferico} <--{resposta[1]}")
    
def recuperaComandos(filename): 
    try: 
        with open(filename, 'rb') as file:
            loaded_array = pickle.load(file)
            return loaded_array
    except:
        return []

def avancaFila(i, filaComandos, historicoComandos):
    """
    Avança a fila de comandos para a próxima tarefa.
    :param i: índice do comando que falhou
    :param filaComandos: lista de comandos a serem processados
    :param historicoComandos: lista de comandos já processados
    :param verbose: flag para exibir mensagens de debug
    """
    filaGCode[i]['conclusao'] = round(time.time())*1000
    historicoComandos.append(filaComandos[i])
    filaComandos.pop(i)
    
    
    with open("fila_comandos.pkl", 'wb') as file:
        pickle.dump(filaComandos, file)
    with open("historico_comandos.pkl", 'wb') as file:
        pickle.dump(historicoComandos, file)
    logDebug(f"Fila e historico de comandos salvos.")   
    
    return filaComandos, historicoComandos

def parseGCode(gcode):
    """
    Processa um gcode em seus elementos e verifica se está correto
    :param string gcode: gcode a ser processado
    """
    # Limpa, quebra os parâmtros e identifica o comando
    gcode = gcode.strip()
    logInfo(f"GCode em processamento: {gcode}")
    params = gcode.split()
    comando = params[0]

    # Verifica se o comando é suportado.
    if COMANDOS_SUPORTADOS[comando] == None:
        logError(f"Comando {comando} não suportado.")
        return False, f"Comando {comando} não suportado."
    
    # Verifica os parametros do comando
    elif COMANDOS_SUPORTADOS[comando]["numParams"] > len(params):
        logError(f"Parâmetros insuficientes para {comando} (Esperados {COMANDOS_SUPORTADOS[comando]['numParams']}).")
        return False, f"Parâmetros insuficientes para {comando} (Esperados {COMANDOS_SUPORTADOS[comando]['numParams']})."

    ## TODO: verificar se os parametros obrigatorios estao presentes nos mcodes
#                if parsedGCode[0] == "M12" or parsedGCode[0] == "M13":
#                if not parsedGCode[1].startswith("T"):
#                    processaErro("Ferramenta nao especificada", filaGCode, historico, 0, verbose)

    ## TODO: verificar se é necessario trocar ferramenta
    ## TODO: verificar se é necessário rota de deslocamento
    ## TODO: verificar se o periferico necessario esta disponivel
    # ...



    # Tudo certo, retorna
    return True, {
        'comando': comando,
        'gcode': gcode,
        'periferico': COMANDOS_SUPORTADOS[comando]['periferico'],
        'idleMotor': COMANDOS_SUPORTADOS[comando]['idleMotor']
    }

def trocaFerramenta(indexFerramenta, filaGCode):
    """
    Inclui no início da fila de gcodes uma sequencia de troca de ferramenta para um índice definido
    """
    # TODO
    return False


def tiraFoto(verbose):
    
    # Open the webcam (0 is the default camera)
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)  # Use CAP_V4L2 for better compatibility on Linux/RPi

    if not cap.isOpened():
        return False, "Error: Could not access the webcam."

    # Capture a single frame
    ret, frame = cap.read()
    if ret:
        timestamp = int(time.time() * 1000)  # Get current time in milliseconds
        filename = f"captured_image_{timestamp}.jpg" # Set the filename
        save_dir = os.path.abspath("/home/cyberlavrador2/Pictures") # Get the folder
        image_path = os.path.join(save_dir, filename) # Set the path
        cv2.imwrite(image_path, frame)  # Save the captured image
        logInfo(f"Imagem salva.")
        # Release the camera resource
        cap.release()
        return True, "ok"
    else:
        # Release the camera resource
        cap.release()
        return False, "Failed to capture image"

def processaFila(filaGCode, historicoGCode, GRBL, GRBLBuffer, HEAD, PUMP, tarefaAtual):
    """
    Processa todos os comandos de um array, movendo-os para o array de historico.

    :param array filaGCode: fila de gcodes a serem processados 
    :param array historicoGCode: historico de gcodes processados
    :param serial GRBL: conexao serial com GRBL
    :param int GRBLBuffer: tamanho do buffer do GRBL disponivel
    :param serial HEAD: conexao serial com HEAD
    :param serial PUMP: conexao serial com PUMP
    """
    while len(filaGCode) > 0:
    # Enquanto há comandos na fila...

        # Verifica se o comando é compreensível. Se não for, processa o erro
        # e continua com o próximo comando (da próxima tarefa, pois processar
        # o erro pula os comandos restantes da tarefa)
        parsedGCode = parseGCode(filaGCode[0]["instrucao"])
        if not parsedGCode[0]:
            processaErroGCode (parsedGCode[1], filaGCode, historicoGCode)
            continue
        
        # Verificar se o comando exige motores parados. Isso é necessário pois há gcodes
        # que precisam ser executados em uma posicao exata, o que se verifica com o GRBL
        # respondendo com estado "Idle". Portanto, se os motores não estao parados, encerra
        # o processamento da fila de comandos, pois não sabemos quanto tempo vai levar para
        # concluir a operação sendo realizada pelo GRBL.
        estadoGRBL = obterEstadoGRBL(GRBL)
        if not estadoGRBL: processaErroGCode(f"Falha na comunicacao com GRBL", filaGCode, historicoGCode)
        if parsedGCode[1]['idleMotor']:
            if estadoGRBL['estado'] != 'Idle':
                logInfo(f"Aguardando motores...")
                break

        # Se o comando pode ser enviado, manda para o periferico de destino
        elif parsedGCode[1]['periferico'] == 'GRBL':
            # No caso dos comandos que são enviados para o GRBL, as condições que são verificadas
            # são:
            # - GRBL desconectado --> aguarda o próximo loop (espera reestabelecer conexão)
            # - GRBL em alarme    --> aguarda o próximo loop (espera destravar GRBL)
            # - buffer GRBL cheio --> aguarda o próximo loop (espera liberar buffer)
            if not GRBL or not estadoGRBL: 
                logInfo(f"Aguardando conexão com GRBL...")
                break
            if not GRBLBuffer:
                logInfo(f"Buffer de comandos do GRBL cheio...")
                break
            if estadoGRBL == "Alarm":
                logInfo(f"Aguardando resolução do alarme do GRBL...")
                break

            # Está implementado um protocolo simples de Send-Response, baseado no estado
            # do buffer de comandos do GRBL.
            processaEnvioGCode(GRBL, 'GRBL', parsedGCode[1]['gcode'], filaGCode)
            GRBLBuffer = GRBLBuffer - 1
            if resposta[0]: processaSucessoGCode(resposta[1], filaGCode, historicoGCode)
            else:           processaErroGCode(resposta[1], filaGCode, historicoGCode)
            continue

        elif parsedGCode[1]['periferico'] == "HEAD":
            # No caso dos comandos que são enviados para o GRBL, as condições que são verificadas
            # são:
            # - HEAD desconectado      --> aguarda o próximo loop (espera reestabelecer conexão)
            # - HEAD TOOL incompativel --> inclui uma rotina de troca de ferramenta

            if not HEAD:
                logInfo(f"Aguardando conexão com GRBL...")
                break
#            if not resposta["HEAD"]["Tool"] == parsedGCode[1][1:]:
#                logInfo(f"Trocando ferramenta...")
#                trocaFerramenta(0, filaGCode)

            # Está implementado um protocolo simples de Send-Response. Como o HEAD
            # não suporta, atualmente, nenhum comando que não seja realizado de imediato
            # não houve preocupação com o buffer de comandos.
            processaEnvioGCode(HEAD, 'HEAD', parsedGCode[1]['gcode'], filaGCode)
            if resposta[0]: processaSucessoGCode(resposta[1], filaGCode, historicoGCode)
            else:           processaErroGCode(resposta[1], filaGCode, historicoGCode)
            continue
                    
        elif parsedGCode[1]['periferico'] == "CAMERA":
            # Está implementado um protocolo simples de Send-Response. Como a CAMERA
            # não suporta, atualmente, nenhum comando que não seja realizado de imediato
            # não houve preocupação com o buffer de comandos.
            if parsedGCode[0] == "M240":
                logDebug(f"CAMERA -->{parsedGCode[1]['gcode']}")
                resposta = tiraFoto()
                logDebug(f"CAMERA <--{resposta[1]}")
                if resposta[0]: processaSucessoGCode(resposta[1], filaGCode, historicoGCode)
                else:           processaErroGCode(resposta[1], filaGCode, historicoGCode)
                continue

        elif parsedGCode[1]['periferico'] == "PUMP":
            # Está implementado um protocolo simples de Send-Response. Como o PUMP
            # não suporta, atualmente, nenhum comando que não seja realizado de imediato
            # não houve preocupação com o buffer de comandos.
            logDebug(f"PUMP -->{parsedGCode[1]['gcode']}")
            resposta = [True, "bypass"]
            logDebug(f"PUMP <--{resposta[1]}")
            if resposta[0]: processaSucessoGCode(resposta[1], filaGCode, historicoGCode)
            else:           processaErroGCode(resposta[1], filaGCode, historicoGCode)
            #TODO implementar comandos de bombeamento
            #resposta = enviaGCode(PUMP, instrucao)

        # Se não é conhecido o periférico, registra o erro e passa para a próxima tarefa.
        else:
            processaErroGCode(f"Periferico {COMANDOS_SUPORTADOS[parsedGCode[0]]['periferico']} desconhecido.", filaGCode, historicoGCode)
