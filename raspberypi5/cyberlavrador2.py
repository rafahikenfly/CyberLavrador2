from firebase import initialize_firebase
from firebase import read_fitered_realtime_db
from firebase import read_realtime_db
from grbl import connect_to_grbl
from grbl import unlock_grbl
from grbl import enviaGCode

from taskManager import filtrarPorPrazo
from taskManager import filtrarPorFerramenta
from taskManager import filtrarPorCondicao
from taskManager import ordenarListaPorChave
from taskManager import preparaComandos
from taskManager import processaTarefa
from taskManager import falhaTarefa
from taskManager import concluiTarefa
from taskManager import anotaTarefa

import time

verbose = True

terrain = "-OEy62gRLp6VMWWHs7Kt"
pathTarefas = "/loteamento/"+ terrain + "/tarefas"
pathCanteiros = "/loteamento/"+ terrain + "/canteiros"
pathBOK = "/bok/classes"


GRBLport = "/dev/ttyACM0"
baudrate = 115200  # Velocidade padrao do GRBL

FERRAMENTAS = {
    "SensorDistancia": False,
    "Rocadeira": True,
    "Laser": False,
    "Camera": False,
    "Agua": True,
    "Fertilizante": True,
    "Medicamento": False,
    "Vacuo": False,
    "SensorUmidade": False,
    "SensorTemperatura": False,
    "SensorPH": False,
    "Arado": False,
}

intervaloFila = 3600
tamanhoLoteConsulta = 100
tamanhoLoteProcessamento = 5


filaComandos = []
historicoComandos = []
objetoTeste = { "posicao": {
    "X": 100,
    "Y": 90,
    "Z": 80,
}}


if __name__ == "__main__":
    #inicializa firebase
    initialize_firebase()
    #conecta com o GRBL
    GRBL = connect_to_grbl(GRBLport, baudrate)
    print(enviaGCode(GRBL,"?"))
    unlock_grbl(GRBL)

    #obtem a base de conhecimento atualizada
    classes = read_realtime_db(pathBOK)
    canteiros = read_realtime_db(pathCanteiros)

    while True:
        #busca tarefas
        tarefasAguardando = read_fitered_realtime_db(pathTarefas, "estado", "Aguardando", tamanhoLoteConsulta)
        verbose and print("Há", len(tarefasAguardando), "tarefa(s) aguardando realização.")

        #filtra aquelas que podem ser realizadas pelo robo e pelas condições da classe, ordenando por prazo
        tarefasVencidas = filtrarPorPrazo(tarefasAguardando,time.time())
        tarefasComFerramenta = filtrarPorFerramenta(tarefasAguardando,classes,FERRAMENTAS)
        verbose and print("Encontrei", len(tarefasComFerramenta), "tarefa(s) que sou capaz de realizar.")
        tarefasComCondicao = filtrarPorCondicao(tarefasComFerramenta,classes)
        print("Há", len(tarefasComCondicao[1]), "tarefa(s) disponíveis para realização.")
        listaDeTarefas = ordenarListaPorChave(tarefasComCondicao[1],"prazo")

        #para as tarefas da lista, prepara os comandos e marca a tarefa como processada
        for tarefa in listaDeTarefas[:tamanhoLoteProcessamento]:
            for instrucao in preparaComandos(classes.get(tarefa.get("classe")).get("manejo").get(tarefa.get("manejo")), canteiros.get(tarefa.get("objeto"))):
                filaComandos.append({
                    "tarefa": tarefa.get("chave"),
                    "instrucao": instrucao,
                    "resposta": "",
                    "estado": "fila",
                })
            processaTarefa(tarefa.get("chave"))
        
        #envia instrucoes para os dispositivos devidos e registra a resposta
        i = 0
        while i < len(filaComandos):
            comando = filaComandos[i]
            instrucao = comando.get("instrucao")

            # comandos G vão sempre ser enviados para o GRBL
            if instrucao.startswith("G"):
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} GRBL -->{instrucao}")
                resposta = enviaGCode(GRBL, instrucao)
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} GRBL <--{resposta}")
                if resposta == "ok": comando["estado"] = "enviado"
                else:  comando["estado"] = "erro"

            # comandos MOTOR, LASER, VACUO, BOMBA são enviados para a FERRAMENTA
            elif instrucao.startswith("MOTOR"):
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} FERAMENTA -->{instrucao}")
                resposta = "Motor não instalado"
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} FERRAMENTA <--{resposta}")
                if resposta == "ok": comando["estado"] = "enviado"
                else:  comando["estado"] = "enviado"
            elif instrucao.startswith("LASER"):
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} FERAMENTA -->{instrucao}")
                resposta = "Laser não instalado"
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} FERRAMENTA <--{resposta}")
                if resposta == "ok": comando["estado"] = "enviado"
                else:  comando["estado"] = "erro"
            elif instrucao.startswith("VACUO"):
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} FERAMENTA -->{instrucao}")
                resposta = "Vácuo não instalado"
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} FERRAMENTA <--{resposta}")
                if resposta == "ok": comando["estado"] = "enviado"
                else:  comando["estado"] = "erro"
            elif instrucao.startswith("BOMBA"):
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} FERAMENTA -->{instrucao}")
                resposta = "Bomba não instalado"
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} FERRAMENTA <--{resposta}")
                if resposta == "ok": comando["estado"] = "enviado"
                else:  comando["estado"] = "erro"

            # comandos VALVULA são enviados para válvulas
            elif instrucao.startswith("VALVULA"):
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} VALVULA -->{instrucao}")
                resposta = "Válvula não instalada"
                verbose and print(f"{time.strftime('%H:%M:%S')} {time.time() % 1:.6f} VALVULA <--{resposta}")
                if resposta == "ok": comando["estado"] = "enviado"
                else:  comando["estado"] = "erro"
            else:
                comando["resposta"] = "Instrução desconhecida"
                comando["estado"] = "erro"
            historicoComandos.append(comando)

            tarefaID = comando["tarefa"]

            # se houve erro, registra no RTD e corre a fila de tarefas até a próxima tarefa
            if comando["estado"] == "erro":
                print(f"Erro na execução da tarefa {tarefaID}.")
                falhaTarefa(tarefaID)
                while comando["tarefa"] == tarefaID: 
                    verbose and print(f"pulando comando {comando}.")
                    i = i + 1
                    if i == len(filaComandos): break
                    filaComandos[i]["estado"] = "cancelado"
                    comando = filaComandos[i]

            # se é o último comando da fila ou da tarefa, registra conclusão e segue o loop
            elif i == len(filaComandos) - 1 or filaComandos[i+1]["tarefa"] != tarefaID:
                print(f"Tarefa {tarefaID} executada.")
                concluiTarefa(tarefaID)
                
            #avanca
            i = i + 1
        #limpa a fila
        print("Fim da lista de comandos")
        for x in filaComandos:
            historicoComandos.append(x)
        filaComandos = []
        verbose and print("Histórico:", historicoComandos)
        time.sleep(intervaloFila)