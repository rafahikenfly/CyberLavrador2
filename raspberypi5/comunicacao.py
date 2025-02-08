import serial
import time

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning


def conectaPorta(port, baudrate=115200, nome = "Periferico desconhecido"):
    """
    Conecta ao Arduino GRBL via porta serial.
    """
    try:
        ser = serial.Serial(port, baudrate)
        time.sleep(2)  # Aguarde para o GRBL inicializar
        ser.flushInput()  # Limpa o buffer de entrada
        logInfo (f"{nome} conectado a porta {port}")
        
        return ser
    except Exception as e:
        logError(f"Erro ao estabelecer conexao serial para {nome}: {e}")
        return False

def fechaConexaoGRBL(ser):
    """
    Fecha a conexao serial.
    """
    if ser:
        ser.close()
        logInfo("Conexao encerrada.")

# Comunicação e interpretação
def enviaGCode(ser, gcode):
    """
    Envia comandos G-code ao GRBL.

    :param ser: porta serial para envio
    :param gcode: string a ser enviada
    :return [ok?, resposta]
    """
    if not ser:
        return False, "Conexao serial não estabelecida."

    try:
        gcode.strip() + '\n'  # Adiciona uma nova linha ao comando
        ser.write(gcode.encode('utf-8'))  # Envia o comando
        time.sleep(0.5) #delay da resposta
        response = ser.readline().decode('utf-8').strip()  # Le a resposta
        return True, response
    except Exception as e:
        return False, f"Erro ao enviar gcode: {gcode[:-1]}"

def obterEstado(ser):
    try:
        gcode = '?'
        ser.write(gcode.encode('utf-8')) 
        time.sleep(0.5) #delay da resposta
        response = ser.readline().decode('utf-8').strip()  # Le a resposta
        if response.startswith("<"):
            # Extrai os dados de uma resposta de estado
            return True, response
        else:
            return False
    except Exception as e:
        return False
