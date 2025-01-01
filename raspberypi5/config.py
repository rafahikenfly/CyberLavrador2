
"""
Configurações do sistema

FERRAMENTAS: Dicionário com as ferramentas disponíveis para o CyberLavrador.
QUEUE: Dicionário com as configurações de fila do CyberLavrador.
COMANDOS_SUPORTADOS: Lista com os comandos suportados pelo CyberLavrador. Cada comando é um dicionário com as seguintes chaves:
    - periferico: Periférico de destino do comando (HEAD, PUMP, CAME). Esta chave determina para quem o comando será enviado pelo gerenciador de comandos.
    - elemento: Elemento de destino do comando (RELAY, MOSFET, CAMERA, FERRAMENTA). Esta chave é interpretada para enviar o comando correto para o periférico.
    - indice: Índice do elemento de destino do comando. Esta chave é interpretada para enviar o comando correto para o periférico.
"""
FERRAMENTAS = {
    "SensorDistancia": {
        "instalada": False,
    },
    "Rocadeira": {
        "instalada": True,
    },
    "Laser": {
        "instalada": False,
    },
    "Camera": {
        "instalada": False,
    },
    "Agua": {
        "instalada": True,
    },
    "Fertilizante": {
        "instalada": True,
    },
    "Medicamento": {
        "instalada": False,
    },
    "Vacuo": {
        "instalada": False,
    },
    "SensorUmidade": {
        "instalada": False,
    },
    "SensorTemperatura": {
        "instalada": False,
    },
    "SensorPH": {
        "instalada": False,
    },
    "Arado": {
        "instalada": False,
    },
}
QUEUE = {
    "loteConsulta": 100,
    "loteProcessamento": 5
}
COMANDOS_SUPORTADOS = {
    "M0": {
        "periferico": "HEAD",
        "descricao": "SHADOW ON",
        "elemento": "RELAY",
        "indice": 0,
    },
    "M1": {
        "periferico": "HEAD",
        "descricao": "SHADOW OFF",
        "elemento": "RELAY",
        "indice": 1,
    },
    "M2": {
        "periferico": "HEAD",
        "descricao": "STOP FLUID",
        "elemento": "RELAY",
        "indice": 2,
    },
    "M3": {
        "periferico": "HEAD",
        "descricao": "MOTOR ON",
        "elemento": "RELAY",
        "indice": 3
    },
    "M4": {
        "periferico": "HEAD",
        "descricao": "LASER ON",
        "elemento": "MOSFET",
        "indice": 0
    },
    "M5": {
        "periferico": "HEAD",
        "descricao": "MOTOR OFF",
        "elemento": "CAMERA",
        "indice": 0
    },
    "M6": {
        "periferico": "HEAD",
        "descricao": "LASER OFF",
        "elemento": "FERRAMENTA",
        "indice": 1
    },
    "M7": {
        "periferico": "PUMP",
        "descricao": "FLUD 1 ON",
        "elemento": "FERRAMENTA",
        "indice": 2
    },
    "M8": {
        "periferico": "PUMP",
        "descricao": "FLUD 2 ON",
        "indice": 3
    },
    "M9": {
        "periferico": "PUMP",
        "descricao": "FLUD 3 ON",
        "indice": 4
    },
    "M10": {
        "periferico": "HEAD",
        "descricao": "VACUUM ON",
        "indice": 4
    },
    "M11": {
        "periferico": "HEAD",
        "descricao": "VACUUM OFF",
        "indice": 4
    },
}
