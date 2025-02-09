from comunicacao import obterEstado

def interpretaErroHEAD(message):
    # Mapeamento de codigos de erro do HEAD
    error_codes = {
        0: "Erro genérico",
    }
    error_code = int(message.split(":")[1])
    return (f"{error_code}: {error_codes.get(error_code)}")

def interpretaStatusHEAD(message):
    """
    Interpreta uma mensagem de estado do HEAD.

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
            if part.startswith('Clearance:'):
                # Distância da cabeça ao obstáculo mais próximo
                positions = list(map(int, part[10:].split(',')))
                state['clearance'] = {'Top': positions[0], 'Bottom': positions[1], 'Left': positions[2], 'Right': positions[3]}
            elif part.startswith("Relay:"):
                # Estado dos relays
                values = list(map(bool, part[6:].split(",")))
                state['relayState'] = values
            elif part.startswith('Tool:'):
                # Ferramenta
                state['tool'] = part[5:]
            elif part.startswith('Data:'):
                # Dados do sensor
                values = list(map(int, part[5:].split(",")))
                state['relayState'] = values
            elif part.startswith("Bf:"):
                # Buffer
                state['lookahead_buffer'] = 99 #TODO: Depois de ajustar o código da ferramenta, atualizar aquipart[3:]        
        return state

    except Exception as e:
        return {"error": f"Erro ao interpretar a mensagem: {str(e)}"}

def obterEstadoHEAD(ser):
    status = obterEstado(ser)
    if status: return interpretaStatusHEAD(status[1])
    else: return False

def interpretaRespostaHEAD(message):
    # Verificar se a resposta contem um erro
    if message.startswith("error:"):
        # Extrai o codigo do erro e retorna a descricao do erro
        return False, f"erro: {interpretaErroHEAD(message)}"
    elif message.startswith("ok"):
        # resposta ok
        return True, f"ok"
    else:
        # Resposta incompreendida
        return False, f"erro: Resposta não compreendida: {message}"
    
