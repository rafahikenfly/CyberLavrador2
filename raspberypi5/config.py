
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
    },
    "G1": {
        "periferico": "GRBL",
        "descricao": "Movimento linear de corte: G3 [X{} Y{} Z{}] [F{}]",
        "idleMotor": False,   
    },
    "G2": {
        "periferico": "GRBL",
        "descricao": "Arco de corte em sentido horario: G2 [X{} Y{}] [J{} I{} || R{}] [F{}]",
        "idleMotor": True,   
    },
    "G3": {
        "periferico": "GRBL",
        "descricao": "Arco de corte em sentido anti-horario: G3 [X{} Y{}] [J{} I{} || R{}] [F{}]",
        "idleMotor": True,   
    },
    "G4": {
        "periferico": "GRBL",
        "descricao": "Pausa a execucao por P segundos: G4 P{}",
        "idleMotor": False,   
    },
    "G17": {
        "periferico": "GRBL",
        "descricao": "Define plano de arco de corte XY: G17",
        "idleMotor": False,   
    },
    "G18": {
        "periferico": "GRBL",
        "descricao": "Define plano de arco de corte ZX: G18",
        "idleMotor": False,   
    },
    "G19": {
        "periferico": "GRBL",
        "descricao": "Define plano de arco de corte YZ: G19",
        "idleMotor": False,   
    },
    "G20": {
        "periferico": "GRBL",
        "descricao": "Define unidade de posicao e distancia em polegadas: G20",
        "idleMotor": False,   
    },
    "G21": {
        "periferico": "GRBL",
        "descricao": "Define unidade de posicao e distancia em milimetros: G21",
        "idleMotor": False,   
    },
    "G90": {
        "periferico": "GRBL",
        "descricao": "Define unidade de posicao e distancia a partir da origem: G90",
        "idleMotor": False,   
    },
    "G91": {
        "periferico": "GRBL",
        "descricao": "Define unidade de posicao e distancia a partir da posicao atual: G91",
        "idleMotor": False,   
    },
    "M0": {
        "periferico": "HEAD",
        "descricao": "SHADOW ON",
        "elemento": "RELAY",
        "indice": 0,
        "idleMotor": False,   
    },
    "M1": {
        "periferico": "HEAD",
        "descricao": "SHADOW OFF",
        "elemento": "RELAY",
        "indice": 1,
        "idleMotor": False,   
    },
    "M2": {
        "periferico": "PUMP",
        "descricao": "STOP FLUID",
        "elemento": "RELAY",
        "indice": 2,
        "idleMotor": True,   
    },
    "M3": {
        "periferico": "HEAD",
        "descricao": "MOTOR ON",
        "elemento": "RELAY",
        "indice": 3,
        "idleMotor": True,   
    },
    "M4": {
        "periferico": "HEAD",
        "descricao": "LASER ON",
        "elemento": "MOSFET",
        "indice": 0,
        "idleMotor": False,   
    },
    "M5": {
        "periferico": "HEAD",
        "descricao": "MOTOR OFF",
        "elemento": "CAMERA",
        "indice": 0,
        "idleMotor": True,   
    },
    "M6": {
        "periferico": "HEAD",
        "descricao": "LASER OFF",
        "elemento": "FERRAMENTA",
        "indice": 1,
        "idleMotor": False,   
    },
    "M7": {
        "periferico": "PUMP",
        "descricao": "PUMP 1 ON",
        "elemento": "FERRAMENTA",
        "indice": 2,
        "idleMotor": True,   
    },
    "M8": {
        "periferico": "PUMP",
        "descricao": "PUMP 2 ON",
        "indice": 3,
        "idleMotor": True,   
    },
    "M9": {
        "periferico": "PUMP",
        "descricao": "PUMP 3 ON",
        "indice": 4,
        "idleMotor": True,   
    },
    "M10": {
        "periferico": "HEAD",
        "descricao": "VACUUM ON",
        "indice": 4,
        "idleMotor": True,   
    },
    "M11": {
        "periferico": "HEAD",
        "descricao": "VACUUM OFF",
        "indice": 4,
        "idleMotor": True,   
    },
    "M240": {
        "periferico": "CAMERA",
        "descricao": "TRIGGER CAMERA",
        "idleMotor": True,   
    }    
}
