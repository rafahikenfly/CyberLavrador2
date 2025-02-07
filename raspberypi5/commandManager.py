from grbl import enviaGCode
from taskManager import falhaTarefa
from taskManager import concluiTarefa
from config import COMANDOS_SUPORTADOS
import time
import pickle
import cv2
import os

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning

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
    logWarning(f"Erro na execução da tarefa {tarefaErro}, executando {filaComandos[i]['instrucao']}: {erro}")
    falhaTarefa(tarefaErro, erro)

    # Move comando para histórico
    avancaFila(i, filaComandos, historicoComandos)

    # Cancela comandos da tarefa
    while i<len(filaComandos) and filaComandos[i]["tarefa"] == tarefaErro:
        logDebug(f"Pulando comando {filaComandos[i]} por falha na tarefa relacionada.")
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
        logInfo(f"Tarefa {tarefa} concluida.")
        concluiTarefa(tarefa)
    avancaFila(i, filaComandos, historicoComandos)
    return filaComandos, historicoComandos

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
    historicoComandos.append(filaComandos[i])
    filaComandos.pop(i)
    
    
    with open("fila_comandos.pkl", 'wb') as file:
        pickle.dump(filaComandos, file)
    with open("historico_comandos.pkl", 'wb') as file:
        pickle.dump(historicoComandos, file)
    logDebug(f"Fila e historico de comandos salvos.")   
    
    return filaComandos, historicoComandos

def parseComando(comando):
    # Split the string at the first blank space
    code = comando.split(' ', 1)[0]
    return [code, ""]

def trocaFerramenta(indexFerramenta = 0, filaComandos = [], verbose = False):
    
    logInfo(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} Trocando ferramenta: {indexFerramenta}")
    # TODO


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

def processaFilaComandos(GRBL, HEAD, PUMP, filaComandos = [], historicoComandos = [], verbose = False, GRBLBuffer = 16):
    """
    Processa todos os comandos de um array, movendo-os para o array de historico.
    @param GRBL: conexao serial
    @param HEAD: conexao serial
    @param PUMP: conexao serial
    @param filaComandos: []
    @param historicoComandos: []
    @param verbose 
    """
    # Enquanto há comandos na fila...
    while len(filaComandos) > 0:
        
        instrucao = filaComandos[0]["instrucao"]
        logInfo(f"Instrucao em processamento: {instrucao}")
        
        # Consulta dicionario de comandos suportados
        parsed = parseComando(filaComandos[0]["instrucao"])

        # Primeiro verifica se o comando é suportado.
        # Se não for, registra o erro e passa para o próximo comando.
        if COMANDOS_SUPORTADOS[parsed[0]] == None:
            processaErroComando ("Comando desconhecido: " + parsed[0], filaComandos, historicoComandos, 0, verbose)
            continue


        # Antes de se preocupar com o comando em si, precisa verificar se ele exije motores parados.
        # Comandos com processamento muito longo ou comandos que precisam ser executados em uma posicao exata
        # tem essa caracteristica. Isso se verifica com o GRBL respondendo com estado "Idle".
        # Se os motores nao estao parados, encerra o processamento da fila de comandos, pois não sabemos quanto
        # tempo vai levar para concluir a operação sendo realizada pelo GRBL.
        
        # No caso de mais de 15 comandos enviados para o GRBL em sequencia, para manter o reporte de estado,
        # Forca uma parada para motores assim que 15 comandos em sequencia sao enviados para o GRBL
        # TODO: sera possivel verificar qual o tamanho do buffer disponivel?
        
        if COMANDOS_SUPORTADOS[parsed[0]]['idleMotor'] or not GRBLBuffer:
            resposta = enviaGCode(GRBL, "?")
            if not resposta[0] or resposta[1]["estado"] != "Idle":
                logInfo(f"Aguardando motores ate a proximo loop.")
                break
        elif COMANDOS_SUPORTADOS[parsed[0]]['periferico'] == "GRBL":
            GRBLBuffer = GRBLBuffer - 1

        # Se o comando pode ser enviado, manda para o periferico de destino
        # TODO: aprimorar para um codigo tipo function dispatch
        if COMANDOS_SUPORTADOS[parsed[0]]['periferico'] == "GRBL":
            if not GRBL: 
                processaErroComando("GRBL desconectado", filaComandos,historicoComandos, 0, verbose)
                continue
            
            # Está implementado um protocolo simples de Send-Response. Por isso não é preciso verificar se
            # o GRBL está disponível para receber comandos. Caso o robô esteja muito lento, é possível
            # implementar um protocolo que utiliza o buffer serial do GRBL.
            logDebug(f"GRBL -->{instrucao}")
            resposta = enviaGCode(GRBL, instrucao)
            logDebug(f"GRBL <--{resposta[1]}")
            if resposta[0]: processaSucessoComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
            else:           processaErroComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
            continue

        elif COMANDOS_SUPORTADOS[parsed[0]]['periferico'] == "HEAD":
            if not HEAD:
                processaErroComando("HEAD desconectado", filaComandos,historicoComandos, 0, verbose)
                continue
            if parsed[0] == "M12" or parsed[0] == "M13":
                if not parsed[1].startswith("T"):
                    processaErro("Ferramenta nao especificada", filaComandos, historico, 0, verbose)
                    continue
                if not estado["HEAD"]["Tool"] == parsed[1][1:]:
                    trocaFerramenta(parsed[1][1:], filaComandos, verbose)

            logDebug(f"HEAD -->{instrucao}")
            resposta = enviaGCode(HEAD, instrucao)
            logDebug(f"HEAD <--{resposta[1]}")
            if resposta[0]: processaSucessoComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
            else:           processaErroComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
            continue
                    
        elif COMANDOS_SUPORTADOS[parsed[0]]['periferico'] == "CAMERA":
            if parsed[0] == "M240":
                logDebug(f"CAMERA -->{instrucao}")
                resposta = tiraFoto(verbose)
                logDebug(f"CAMERA <--{resposta[1]}")
                if resposta[0]: processaSucessoComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
                else:           processaErroComando(resposta[1], filaComandos, historicoComandos, 0, verbose)
                continue

        elif COMANDOS_SUPORTADOS[parsed[0]]['periferico'] == "PUMP":
            logDebug(f"PUMP -->{instrucao}")
            resposta = [True, "bypass"]
            logDebug(f"PUMP <--{resposta[1]}")
            processaSucessoComando("ok: não implementado", filaComandos, historicoComandos, 0, verbose)
            #TODO implementar comandos de bombeamento
            #resposta = enviaGCode(PUMP, instrucao)
        # Se não é um comando suportado, registra o erro e passa para o próximo comando.
        else:
            processaErroComando("Periferico " + COMANDOS_SUPORTADOS[parsed[0]] + " associado a " + instrucao + "desconhecido.", filaComandos, historicoComandos, 0, verbose)
