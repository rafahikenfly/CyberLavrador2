import serial
import time

from config import logDebug
from config import logInfo
from config import logError
from config import logWarning


# GRBLStatus = ["Idle", "Run", "Hold", "Jog", "Alarm", "Door", "Check", "Home", "Sleep"]

# Conexão
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
        if gcode != '?': gcode = gcode.strip() + '\n'  # Adiciona uma nova linha ao comando
        ser.write(gcode.encode('utf-8'))  # Envia o comando
        time.sleep(0.5) #delay da resposta
        response = ser.readline().decode('utf-8').strip()  # Le a resposta
        # Verificar se a resposta contem um erro
        if response.startswith("error:"):
            # Extrai o codigo do erro e retorna a descricao do erro
            return False, "erro "+ interpretaErroGRBL(response)
        elif response.startswith("<"):
            # Extrai os dados de uma resposta de estado
            return True, interpretaStatusGRBL(response)
        else:
            return True, response
    except Exception as e:
        return False, "Erro ao enviar gcode: " + gcode[:-1]


def interpretaErroGRBL(message):
    # Mapeamento de codigos de erro do GRBL
    error_codes = {
        1: "G-code words consist of a letter and a value. Letter was not found.",
        2: "Numeric value format is not valid or missing an expected value.",
        3: "Grbl '$' system command was not recognized or supported.",
        4: "Negative value received for an expected positive value.",
        5: "Homing cycle is not enabled via settings.",
        6: "Minimum step pulse time must be greater than 3usec",
        7: "EEPROM read failed. Reset and restored to default values.",
        8: "Grbl '$' command cannot be used unless Grbl is IDLE. Ensures smooth operation during a job.",
        9: "G-code locked out during alarm or jog state",
        10: "Soft limits cannot be enabled without homing also enabled.",
        11: "Max characters per line exceeded. Line was not processed and executed.",
        12: "(Compile Option) Grbl '$' setting value exceeds the maximum step rate supported.",
        13: "Safety door detected as opened and door state initiated.",
        14: "(Grbl-Mega Only) Build info or startup line exceeded EEPROM line length limit.",
        15: "Jog target exceeds machine travel. Command ignored.",
        16: "Jog command with no '=' or contains prohibited g-code.",
        17: "Laser mode requires PWM output.",
        20: "Unsupported or invalid g-code command found in block.",
        21: "More than one g-code command from same modal group found in block.",
        22: "Feed rate has not yet been set or is undefined.",
        23: "G-code command in block requires an integer value.",
        24: "Two G-code commands that both require the use of the XYZ axis words were detected in the block.",
        25: "A G-code word was repeated in the block.",
        26: "A G-code command implicitly or explicitly requires XYZ axis words in the block, but none were detected.",
        27: "N line number value is not within the valid range of 1 - 9,999,999.",
        28: "A G-code command was sent, but is missing some required P or L value words in the line.",
        29: "Grbl supports six work coordinate systems G54-G59. G59.1, G59.2, and G59.3 are not supported.",
        30: "The G53 G-code command requires either a G0 seek or G1 feed motion mode to be active. A different motion was active.",
        31: "There are unused axis words in the block and G80 motion mode cancel is active.",
        32: "A G2 or G3 arc was commanded but there are no XYZ axis words in the selected plane to trace the arc.",
        33: "The motion command has an invalid target. G2, G3, and G38.2 generates this error, if the arc is impossible to generate or if the probe target is the current position.",
        34: "A G2 or G3 arc, traced with the radius definition, had a mathematical error when computing the arc geometry. Try either breaking up the arc into semi-circles or quadrants, or redefine them with the arc offset definition.",
        35: "A G2 or G3 arc, traced with the offset definition, is missing the IJK offset word in the selected plane to trace the arc.",
        36: "There are unused, leftover G-code words that aren't used by any command in the block.",
        37: "The G43.1 dynamic tool length offset command cannot apply an offset to an axis other than its configured axis. The Grbl default axis is the Z-axis.",
        38: "Tool number greater than max supported value."
    }
    error_code = int(message.split(":")[1])
    return (f"{error_code}: {error_codes.get(error_code)}")
    
def interpretaStatusGRBL(message):
    """
    Interpreta uma mensagem de estado do GRBL.

    :param message: A mensagem de estado no formato "<Status|Componentes...>".
    :return: Dicionario com os componentes da mensagem interpretados.
    """
    if not message.startswith("<") or not message.endswith(">"):
        return {"error": "Formato de mensagem invalido."}

    # Remove os delimitadores <>
    content = message[1:-1]

    # Divide os componentes pelo delimitador |
    parts = content.split("|")

    # Inicializa o dicionario para armazenar os resultados
    state = {}

    try:
        # O primeiro elemento e o estado da maquina (Idle, Run, etc.)
        state["estado"] = parts[0]

        # Processa os demais componentes
        for part in parts[1:]:
            if part.startswith("MPos:"):
                # Posicao da maquina
                positions = list(map(float, part[5:].split(",")))
                state["machine_position"] = {"X": positions[0], "Y": positions[1], "Z": positions[2]}
            elif part.startswith("WPos:"):
                # Posicao do trabalho
                positions = list(map(float, part[5:].split(",")))
                state["work_position"] = {"X": positions[0], "Y": positions[1], "Z": positions[2]}
            elif part.startswith("FS:"):
                # Velocidade de avanco e do spindle
                values = list(map(int, part[3:].split(",")))
                state["feed_rate"] = values[0]
                state["spindle_speed"] = values[1]
            elif part.startswith("Ov:"):
                # Overrides (feed, rapids, spindle)
                values = list(map(int, part[3:].split(",")))
                state["overrides"] = {"feed": values[0], "rapids": values[1], "spindle": values[2]}
            elif part.startswith("A:"):
                # Alarmes
                state["alarm"] = part[2:]
            elif part.startswith("Bf:"):
                # Buffer
                values = list(map(int, part[3:].split(",")))
                state["lookahead_buffer"] = values[0]
                state["rx_buffer"] = values[1]
        
        return state

    except Exception as e:
        return {"error": f"Erro ao interpretar a mensagem: {str(e)}"}

# Alto nível
def destravaGRBL(ser, verbose):
    """
    Destrava o GRBL enviando o comando $X.
    :param ser: porta serial para envio
    """
    if not ser:
        return "Conexao serial não estabelecida."

    try:
        # Envia o comando para destravar
        comando = "$X"
        comando  = comando.strip() + '\n'
        ser.write(comando.encode('utf-8'))
        logDebug(f"GRBL --> $X")

        # Le a resposta do GRBL
        resposta = ser.readline().decode('utf-8').strip() #ok
        resposta = ser.readline().decode('utf-8').strip()      
        logDebug(f"GRBL <-- {resposta}")
    except Exception as e:
        logError(f"Erro ao destravar GRBL: {e}")
