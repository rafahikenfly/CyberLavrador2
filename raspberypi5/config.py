"""
COMANDOS_SUPORTADOS: Lista com os comandos suportados pelo CyberLavrador. Cada comando é um dicionário com as seguintes chaves:
    - periferico: Periférico de destino do comando (HEAD, PUMP, CAME). Esta chave determina para quem o comando será enviado pelo gerenciador de comandos.
    - elemento: Elemento de destino do comando (RELAY, MOSFET, CAMERA, FERRAMENTA). Esta chave é interpretada para enviar o comando correto para o periférico.
    - indice: Índice do elemento de destino do comando. Esta chave é interpretada para enviar o comando correto para o periférico.
"""
COMANDOS_SUPORTADOS = {
    "G0": {
        "periferico": "GRBL",
        "descricao": "Movimento linear rapido: G0 [X{} Y{} Z{}]",
        "idleMotor": False,  
        "numParams": 2,
    },
    "G1": {
        "periferico": "GRBL",
        "descricao": "Movimento linear de corte: G3 [X{} Y{} Z{}] [F{}]",
        "idleMotor": False,   
        "numParams": 2,
    },
    "G2": {
        "periferico": "GRBL",
        "descricao": "Arco de corte em sentido horario: G2 [X{} Y{}] [J{} I{} || R{}] [F{}]",
        "idleMotor": True,   
        "numParams": 3,
    },
    "G3": {
        "periferico": "GRBL",
        "descricao": "Arco de corte em sentido anti-horario: G3 [X{} Y{}] [J{} I{} || R{}] [F{}]",
        "idleMotor": True,   
        "numParams": 3,
    },
    "G4": {
        "periferico": "GRBL",
        "descricao": "Pausa a execucao por P segundos: G4 P{}",
        "idleMotor": False,   
        "numParams": 2,
    },
    "G17": {
        "periferico": "GRBL",
        "descricao": "Define plano de arco de corte XY: G17",
        "idleMotor": False,   
        "numParams": 1,
    },
    "G18": {
        "periferico": "GRBL",
        "descricao": "Define plano de arco de corte ZX: G18",
        "idleMotor": False,
        "numParams": 1,
    },
    "G19": {
        "periferico": "GRBL",
        "descricao": "Define plano de arco de corte YZ: G19",
        "idleMotor": False,
        "numParams": 1,
    },
    "G20": {
        "periferico": "GRBL",
        "descricao": "Define unidade de posicao e distancia em polegadas: G20",
        "idleMotor": False,   
        "numParams": 1,
    },
    "G21": {
        "periferico": "GRBL",
        "descricao": "Define unidade de posicao e distancia em milimetros: G21",
        "idleMotor": False,   
        "numParams": 1,
    },
    "G90": {
        "periferico": "GRBL",
        "descricao": "Define unidade de posicao e distancia a partir da origem: G90",
        "idleMotor": False,   
        "numParams": 1,
    },
    "G91": {
        "periferico": "GRBL",
        "descricao": "Define unidade de posicao e distancia a partir da posicao atual: G91",
        "idleMotor": False,   
        "numParams": 1,
    },
    "M0": {
        "periferico": "HEAD",
        "descricao": "Estende o sombrite: M0",
        "idleMotor": False,
        "numParams": 1,
    },
    "M1": {
        "periferico": "HEAD",
        "descricao": "Recolhe o sombrite: M1",
        "idleMotor": False,   
        "numParams": 1,
    },
    "M2": {
        "periferico": "PUMP",
        "descricao": "Para o bombeamento de fluido no relay I: M2 I{}",
        "idleMotor": True,
        "numParams": 2,
    },
    "M3": {
        "periferico": "HEAD",
        "descricao": "Liga o motor rotativo da cabeça [por P segundos]: M3 [P{}]",
        "idleMotor": True,
        "numParams": 2,
    },
    "M4": {
        "periferico": "HEAD",
        "descricao": "Liga o laser da cabeça [por P segundos]: M4 [P{}]",
        "idleMotor": True,
        "numParams": 1,
    },
    "M5": {
        "periferico": "HEAD",
        "descricao": "Desliga o motor rotativo da cabeça: M5",
        "idleMotor": True,   
        "numParams": 1,
    },
    "M6": {
        "periferico": "HEAD",
        "descricao": "Desliga o laser da cabeça",
        "numParams": 1,
        "idleMotor": False,   
    },
    "M7": {
        "periferico": "PUMP",
        "descricao": "Liga o bombeamento de fluido no relay I [por P segundos]. M7 I{} [P{}]",
        "idleMotor": True,   
        "numParams": 2,
    },
#    "M8": {
#    },
#    "M9": {
#    },
    "M10": {
        "periferico": "HEAD",
        "descricao": "Liga a bomba de vácuo [por P segundos]: M10 [P{}]",
        "idleMotor": True,
        "numParams": 1,
    },
    "M11": {
        "periferico": "HEAD",
        "descricao": "Desliga a bomba de vácuo",
        "idleMotor": True,
        "numParams": 1,
    },
    "M240": {
        "periferico": "CAMERA",
        "descricao": "Tira uma foto com a câmera de cabeça em posição: M240",
        "idleMotor": True,   
        "numParams": 1,
    }    
}


import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime

# Create a directory for logs if it doesn't exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Define log file with a timestamp
log_file = os.path.join(log_dir, "cyberLavrador.log")
handler = TimedRotatingFileHandler(log_file, when="h", interval=12, backupCount=14)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),  # Log to file
        logging.StreamHandler()         # Log to console
    ]
)

logger = logging.getLogger("CyberLavrador 2.0")

def logDebug (mensagem):
    logger.debug(mensagem)

def logError (mensagem):
    logger.error(mensagem)

def logInfo (mensagem):
    logger.info(mensagem)
    
def logWarning (mensagem):
    logger.warning(mensagem)
