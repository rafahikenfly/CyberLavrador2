import serial
import time

def connect_to_grbl(port, baudrate=115200):
    """
    Conecta ao Arduino GRBL via porta serial.
    """
    try:
        ser = serial.Serial(port, baudrate)
        time.sleep(2)  # Aguarde para o GRBL inicializar
        ser.flushInput()  # Limpa o buffer de entrada
        print(f"Conectado ao GRBL na porta {port}")
        return ser
    except Exception as e:
        print(f"Erro ao conectar ao GRBL: {e}")
        return None

def send_gcode(ser, gcode):
    """
    Envia comandos G-code ao GRBL.
    """
    if not ser:
        print("Erro: Conexao serial nao estabelecida.")
        return

    try:
        for command in gcode:
            command = command.strip() + '\n'  # Adiciona uma nova linha ao comando
            ser.write(command.encode('utf-8'))  # Envia o comando
            response = ser.readline().decode('utf-8').strip()  # Le a resposta
            # Verificar se a resposta contem um erro
            if response.startswith("error:"):
                # Extrai o codigo do erro e retorna a descricao do erro
                print(f"Enviado: {command.strip()} | Erro {interpret_grbl_error(response)}")
            elif response.startswith("<") :
                print(interpret_grbl_state(response))
            else:
                print(f"Enviado: {command.strip()} | Resposta: {response}")
    except Exception as e:
        print(f"Erro ao enviar comandos: {e}")

def close_connection(ser):
    """
    Fecha a conexao serial.
    """
    if ser:
        ser.close()
        print("Conexao encerrada.")

def interpret_grbl_error(message):
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
    
def interpret_grbl_state(message):
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
        state["status"] = parts[0]

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
        
        return state

    except Exception as e:
        return {"error": f"Erro ao interpretar a mensagem: {str(e)}"}
    
if __name__ == "__main__":
    # Configuracao
    port = "/dev/ttyACM0"
    baudrate = 115200  # Velocidade padrao do GRBL

    # Lista de comandos G-code
    gcode_commands = [
        "?",  # Define as unidades como milimetros
        "G90",  # Modo de posicionamento absoluto
        "G0 X10 Y10",  # Movimento rapido para X=10, Y=10
        "G1 X20 Y20 F100",  # Movimento linear para X=20, Y=20 com feedrate de 100 mm/min
        "G0 X0 Y0",  # Retorna para a origem
    ]

    # Conectar ao GRBL
    serial_connection = connect_to_grbl(port, baudrate)

    # Enviar comandos G-code
    send_gcode(serial_connection, gcode_commands)

    # Encerrar conexao
    close_connection(serial_connection)
