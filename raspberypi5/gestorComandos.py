from comunicacao import enviaGCode
from grbl import obterEstadoGRBL
from gestorListaTarefas import marcaFalhaTarefa
from gestorListaTarefas import marcaTarefaConcluida
from config import COMANDOS_SUPORTADOS
import time
import pickle
import cv2
import os

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning

def processaErroGCode(erro, filaGCode, tarefaErro, i = 0):
    """
    Processa um erro de comando, pulando para a próxima tarefa da fila (se existente) e registrando a falha.
    :param filaGCode: lista de comandos a serem processados
    :param string erro: string com a descrição do erro
    :param dict tarefaErro: tarefa em que o erro aconteceu
    :param int i=0: índice do comando que falhou
    """
    # Reporta erro no debug e banco de dados
    logError(f"Erro na execução da tarefa {tarefaErro}, executando {filaGCode[i]['instrucao']}: {erro}")
    marcaFalhaTarefa(tarefaErro['key'], erro)
    
def recuperarComandos(filename): 
    try: 
        with open(filename, 'rb') as file:
            filaGCode, tarefaID = pickle.load(file)
            return filaGCode, tarefaID
    except:
        return [], ""

def salvarComandos(filaGCode, tarefaID):
    """
    Salva filaComandos.
    :param filaComandos: lista de comandos a serem processados
    :param historicoComandos: lista de comandos já processados
    """
    with open("comandos.pkl", 'wb') as file:
        pickle.dump((filaGCode, tarefaID), file)
    logDebug(f"FilaGCode, tarefaID e índice salvos.")


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


def processaFilaGCode(filaGCode, GRBL, GRBLBuffer, HEAD, HEADBuffer, PUMP, PUMPBuffer, tarefaID, i = 0):
    """
    Processa todos os comandos de um array, movendo-os para o array de historico.

    :param array filaGCode: fila de gcodes a serem processados
    :param serial GRBL: conexao serial com GRBL
    :param int GRBLBuffer: tamanho do buffer do GRBL disponivel
    :param serial HEAD: conexao serial com HEAD
    :param int HEADBuffer: tamanho do buffer do HEAD disponivel
    :param serial PUMP: conexao serial com PUMP
    :param int PUMPBuffer: tamanho do buffer do PUMP disponivel
    :param str tarefaID: chave da tarefa em execução
    """
    if not GRBL:
        logInfo(f"Aguardando conexão com GRBL...")
        return False

    for j in range(i,len(filaGCode)):
        gcode = filaGCode[j].strip()
        logInfo(f"GCode em processamento: {gcode}")
        params = gcode.split()
        # Verifica se o comando é suportado e tem o número adequado de parâmetros
        if params[0] not in COMANDOS_SUPORTADOS:
            processaErroGCode(f"Comando {params[0]} não suportado.", filaGCode, tarefaID, i)
        elif len(params) < COMANDOS_SUPORTADOS[params[0]]['numParams']:
            processaErroGCode(f"Parâmetros insuficientes para {params[0]} (Esperados {COMANDOS_SUPORTADOS[params[0]]['numParams']}).", filaGCode, tarefaID, i)
        else:
            # Obtem o estado dos motores
            estadoGRBL = obterEstadoGRBL(GRBL)
            if not estadoGRBL: processaErroGCode(f"Falha na comunicacao com GRBL", filaGCode, tarefaID, i)
            if COMANDOS_SUPORTADOS[params[0]]['idleMotor'] and estadoGRBL['estado'] != 'Idle':
                # Verifica se o comando exige motores parados. Isso é necessário pois há gcodes
                # que precisam ser executados em uma posicao exata, o que se verifica com o GRBL
                # respondendo com estado "Idle". Portanto, se os motores não estao parados, encerra
                # o processamento da fila de comandos, pois não sabemos quanto tempo vai levar para
                # concluir a operação sendo realizada pelo GRBL.
                logInfo(f"Aguardando motores...")
                break
            elif COMANDOS_SUPORTADOS[params[0]]['periferico'] == 'GRBL':
                # No caso dos comandos que são enviados para o GRBL, as condições que são verificadas
                # são:
                # - GRBL em alarme    --> aguarda o próximo loop (espera destravar GRBL)
                # - buffer GRBL cheio --> aguarda o próximo loop (espera liberar buffer)
                if not GRBLBuffer:
                    logInfo(f"Buffer de comandos do GRBL cheio...")
                    break
                if estadoGRBL == "Alarm":
                    logInfo(f"GRBL em estado de alarme...")
                    break
                else:
                    logDebug(f"GRBL -->{gcode}")
                    resposta = enviaGCode(GRBL, gcode)
                    logDebug(f"GRBL <--{resposta[1]}")
                    if not resposta[0]:
                        processaErroGCode(resposta[1], filaGCode, tarefaID, i)
                        break
            elif COMANDOS_SUPORTADOS[params[0]]['periferico'] == 'HEAD':
                # No caso dos comandos que são enviados para o HEAD, as condições que são verificadas
                # são:
                # - HEAD desconectado      --> aguarda o próximo loop (espera reestabelecer conexão)
                # TODO: HEAD TOOL incompativel --> inclui uma rotina de troca de ferramenta
                if not HEAD:
                    logInfo(f"Aguardando conexão com HEAD...")
                    break
                if not HEADBuffer:
                    logInfo(f"Buffer de comandos do HEAD cheio...")
                    break
                else:
                    logDebug(f"HEAD -->{gcode}")
                    resposta = enviaGCode(HEAD, gcode)
                    logDebug(f"HEAD <--{resposta[1]}")
                    if not resposta[0]:
                        processaErroGCode(resposta[1], filaGCode, tarefaID, i)
                        break
            elif COMANDOS_SUPORTADOS[params[0]]['periferico'] == 'PUMP':
                # No caso dos comandos que são enviados para o PUMP, as condições que são verificadas
                # são:
                # - PUMP desconectado      --> aguarda o próximo loop (espera reestabelecer conexão)
                # TODO: PUMP TOOL incompativel --> inclui uma rotina de troca de ferramenta
                if not PUMP:
                    logInfo(f"Aguardando conexão com PUMP...")
                    break
                if not PUMPBuffer:
                    logInfo(f"Buffer de comandos do PUMP cheio...")
                    break
                else:
                    logDebug(f"PUMP -->{gcode}")
                    resposta = enviaGCode(PUMP, gcode)
                    logDebug(f"PUMP <--{resposta[1]}")
                    if not resposta[0]:
                        processaErroGCode(resposta[1], filaGCode, tarefaID, i)
                        break
            elif COMANDOS_SUPORTADOS[params[0]]['periferico'] == 'CAMERA':
                # No caso dos comandos que são enviados para a CAMERA, a lógica é outra
                # TODO: qualquer comando da camera está tirando foto
                # TODO: enviar para a camera
                logDebug(f"CAMERA -->{gcode}")
                resposta = tiraFoto()
                logDebug(f"CAMERA <--{resposta[1]}")
                if not resposta[0]:
                    processaErroGCode(resposta[1], filaGCode, tarefaID, i)
                    break
            else:
                # Se não é conhecido o periférico, registra o erro e passa para a próxima tarefa.
                processaErroGCode(f"Periferico {COMANDOS_SUPORTADOS[params[0]]['periferico']} desconhecido.", filaGCode, tarefaID, i)
                break
        i = i + 1
    return i