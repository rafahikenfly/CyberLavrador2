from config import logDebug
from config import logInfo
from config import logError
from config import logWarning

from comunicacao import obterEstado

import time

# GRBLStatus = ["Idle", "Run", "Hold", "Jog", "Alarm", "Door", "Check", "Home", "Sleep"]

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

def obterEstadoGRBL(ser):
    status = obterEstado(ser)
    if status: return interpretaStatusGRBL(status[1])
    else: return False

def interpretaRespostaGRBL(message):
    # Verificar se a resposta contem um erro
    if message.startswith("error:"):
        # Extrai o codigo do erro e retorna a descricao do erro
        return False, f"erro: {interpretaErroGRBL(message)}"
    elif message.startswith("ok"):
        # resposta ok
        return True, f"ok"
    else:
        # Resposta incompreendida
        return False, f"erro: Resposta não compreendida: {message}"
    
# Alto nível
def desativaAlarme(ser):
    """
    Destrava o GRBL enviando o comando $X.
    :param ser: porta serial para envio
    """
    if not ser:
        return "Conexao serial não estabelecida."

    try:
        # Envia o comando para destravar
        comando = '$X' + '\n'
        ser.write(comando.encode('utf-8'))
        logDebug(f"GRBL --> $X")
        time.sleep(0.5) #delay da resposta

        # Le a resposta do GRBL
        resposta1 = ser.readline().decode('utf-8').strip() #[MSG: Caution: Unlocked]
        resposta2 = ser.readline().decode('utf-8').strip() #ok    
        logDebug(f"GRBL <-- {resposta1},{resposta2}")
    except Exception as e:
        logError(f"Erro ao destravar GRBL: {e}")

def desativarMotores(ser):
    """
    Coloca o GRBL em sleep com o comando $SLP.
    :param ser: porta serial para envio
    """
    if not ser:
        return "Conexao serial não estabelecida."
    try:
        # Envia o comando para dormir
        ser.write(b'$SLP\n')
        logDebug(f"GRBL --> $SLP")
        time.sleep(0.5) #delay da resposta

        # Le a resposta do GRBL
        while ser.in_waiting:
            response = ser.readline().decode().strip()
            logDebug(f"GRBL <-- {response}")
    except Exception as e:
        logError(f"Erro ao destravar GRBL: {e}")

def softReset(ser): 
    """
    Reseta o GRBL com o comando $SLP.
    :param ser: porta serial para envio
    """
    if not ser:
        return "Conexao serial não estabelecida."
    try:
        # Envia o comando para destravar
        ser.write(b'\x18')
        logDebug(f"GRBL --> ctrl-x")
        time.sleep(1) #delay da resposta
        # Le a resposta do GRBL
        while ser.in_waiting > 0:  # Check if data is available to read
            data = ser.readline().decode('utf-8', errors='ignore').strip()
            logDebug(f"GRBL <-- {data}")
        
    except Exception as e:
        logError(f"Erro ao destravar GRBL: {e}")
