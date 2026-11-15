import asyncio
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from langchain.tools import tool
import os
import shutil
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# --- CONFIGURACIÓN DEL SERVIDOR MCP (HTTP) ---
# El servidor debe estar arrancado antes: python server_http.py
MCP_URL = "http://127.0.0.1:8000/mcp"
TEMATICAS = ["cocina", "lectura", "deportes"] #cambiar a deporte
RECEPCION_DIR = "/home/pabilion/notasPruebas/recepcion"
NOTES_DIR = "/home/pabilion/notasPruebas/misnotas"

load_dotenv()
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")

def obtener_llm(proveedor: str, modelo: str):

    if proveedor.lower() == "ollama":

        return ChatOllama(
            model=modelo,
            temperature=0,
            base_url="http://localhost:11434"
        )

    elif proveedor.lower() == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("No se ha encontrado GEMINI_API_KEY en el archivo .env")
    
        return ChatGoogleGenerativeAI(
            model=modelo,
            temperature=0,
            google_api_key=GEMINI_API_KEY
        )

    else:
        raise ValueError(f"Proveedor no soportado: {proveedor}")

    
async def ainput(prompt: str) -> str:
    # Permite que el loop de asyncio siga corriendo mientras el usuario escribe
    return await asyncio.to_thread(input, prompt)


async def main():
    # Configurar el LLM
    # llm = ChatOllama(
    #     # model='llama3.1:8b-instruct-q4_K_M',
    #     model='llama3.1:8b',
    #     temperature=0,
    #     base_url="http://localhost:11434"
    #     # base_url="http://10.42.68.45:11434"
    #     # base_url="http://127.0.0.1:11434",
    # )

    #para ollama
    # llm = obtener_llm(
    #     proveedor="ollama",
    #     modelo="llama3.1:8b"
    # )

    #para gemini
    llm = obtener_llm(
    proveedor="gemini",
    modelo="gemini-3.5-flash-lite"
    )

    def clasificar_contenido(contenido: str) -> str:
    
        prompt = f"""
        Analiza el contenido de la siguiente nota y clasifícalo en UNA de estas temáticas: {TEMATICAS}
        IMPORTANTE:
        Deberás de clasificar el contenido según tenga relación con la temática
        Si ninguna temática encaja razonablemente con el contenido,devuelve exactamente: SIN_TEMATICA.

        Contenido de la nota:{contenido}

        Devuelve exclusivamente el nombre de la temática elegida o SIN_TEMATICA.
        No añadas explicaciones.
        """


        ##prueba
        # respuesta = llm.invoke(prompt)

        # tema = respuesta.content.strip().lower()

        respuesta = llm.invoke(prompt)

        contenido_respuesta = respuesta.content

        if isinstance(contenido_respuesta, list):
            contenido_respuesta = "".join(
                bloque.get("text", "")
                for bloque in contenido_respuesta
                if isinstance(bloque, dict)
            )

        tema = contenido_respuesta.strip().lower()

        # if tema not in TEMATICAS:
        #     return "Error: El modelo ha devuelto una temática no válida."

        if tema not in TEMATICAS:
            return None
        
        return tema
    
    def obtener_notas_recepcion() -> dict:
        """
        Devuelve un diccionario con los nombres y contenidos
        de todas las notas de la carpeta de recepción.
        """

        notas = {}

        if not os.path.isdir(RECEPCION_DIR):
            return {"error": "La carpeta de recepción no existe."}

        for nombre_nota in os.listdir(RECEPCION_DIR):

            ruta = os.path.join(RECEPCION_DIR, nombre_nota)

            # Solo procesamos archivos
            if os.path.isfile(ruta):

                try:
                    with open(ruta, "r", encoding="utf-8") as archivo:
                        contenido = archivo.read()

                    notas[nombre_nota] = contenido

                except Exception as e:
                    return {
                        "error": f"No se pudo leer {nombre_nota}: {e}"
                    }

        return notas

    
    def clasificar_notas(notas: dict[str, str]) -> dict[str, str]:
        """
        Clasifica varias notas según su contenido.

        Parámetros:
        - notas: diccionario donde las claves son los nombres
          de las notas y los valores son sus contenidos.

        Devuelve un diccionario donde las claves son los nombres
        de las notas y los valores son las temáticas asignadas.
        """

        resultado = {}

        for nombre_nota, contenido in notas.items():

            tema = clasificar_contenido(contenido)

            resultado[nombre_nota] = tema

        return resultado


    def clasificar_notas_recepcion() -> dict[str, str]:
        """
        Obtiene todas las notas de recepción y las clasifica
        según su contenido.

        Devuelve un diccionario con el nombre de cada nota
        y su temática correspondiente.
        """

        # Obtener todas las notas
        notas = obtener_notas_recepcion()

        # Comprobar si se ha producido un error
        if "error" in notas:
            return notas

        # Comprobar si no hay notas
        if not notas:
            return {}

        resultado = {}

        # Clasificar cada nota
        for nombre_nota, contenido in notas.items():

            tema = clasificar_contenido(contenido)

            resultado[nombre_nota] = tema

        return resultado

    def mover_archivo(nombre_nota: str, tema: str) -> str:
        """
        Mueve una nota desde Recepción a su carpeta temática.
        """

        if tema not in TEMATICAS:
            return f"Error: La temática '{tema}' no está permitida."

        if not nombre_nota or os.path.basename(nombre_nota) != nombre_nota:
            return "Error: Nombre de archivo no válido."

        base_recepcion = os.path.realpath(RECEPCION_DIR)
        base_notas = os.path.realpath(NOTES_DIR)

        if not os.path.isdir(base_recepcion):
            return "Error: La carpeta Recepción no existe."

        if not os.path.isdir(base_notas):
            return "Error: La carpeta de notas no existe."

        if not nombre_nota.endswith(".txt"):
            nombre_nota += ".txt"

        archivo_origen = os.path.realpath(
            os.path.join(base_recepcion, nombre_nota)
        )

        if os.path.commonpath([base_recepcion, archivo_origen]) != base_recepcion:
            return "Error: Acceso denegado."

        if not os.path.isfile(archivo_origen):
            return "Error: El archivo no existe en Recepción."

        try:
            carpeta_destino = os.path.realpath(
                os.path.join(base_notas, tema)
            )

            if os.path.commonpath([base_notas, carpeta_destino]) != base_notas:
                return "Error: Ruta de destino no válida."

            os.makedirs(carpeta_destino, exist_ok=True)

            if not os.path.isdir(carpeta_destino):
                return "Error: El destino no es una carpeta."

            ruta_destino = os.path.join(carpeta_destino, nombre_nota)

            if os.path.exists(ruta_destino):
                return "Error: Ya existe una nota con ese nombre en la temática."

            shutil.move(archivo_origen, ruta_destino)

            return "Archivo clasificado correctamente."

        except Exception as e:
            return f"Error al mover el archivo: {str(e)}"

    def mover_archivos(clasificaciones: dict[str, str]) -> dict:
        """
        Recibe un diccionario con los nombres de las notas
        y sus temáticas, y las mueve a sus carpetas correspondientes.
        """

        resultados = {}

        for nombre_nota, tema in clasificaciones.items():
            resultado = mover_archivo(nombre_nota, tema)
            resultados[nombre_nota] = resultado

        return resultados

    @tool
    def clasificar_y_mover_notas() -> dict:
        """
        Clasifica todas las notas de recepción y las mueve
        a sus carpetas temáticas correspondientes.
        """

        # 1. Clasificar todas las notas
        clasificaciones = clasificar_notas_recepcion()

        # 2. Comprobar si se ha producido algún error
        if "error" in clasificaciones:
            return clasificaciones

        # 3. Comprobar si hay notas para clasificar
        if not clasificaciones:
            return {"mensaje": "No hay notas en la carpeta de recepción."}

        # 4. Separar las notas válidas de las pendientes
        notas_validas = {
            nota: tema
            for nota, tema in clasificaciones.items()
            if tema in TEMATICAS
        }

        notas_pendientes = {
            nota: tema
            for nota, tema in clasificaciones.items()
            if tema not in TEMATICAS
        }

        # 5. Mover únicamente las notas válidas
        if notas_validas:
            resultados = mover_archivos(notas_validas)
        else:
            resultados = {}

        # 6. Devolver los resultados
        return {
            "clasificaciones": clasificaciones,
            "movimientos": resultados,
            "notas_pendientes": notas_pendientes
        }
    
        # # 4. Comprobar que las clasificaciones son válidas
        # if any(tema not in TEMATICAS for tema in clasificaciones.values()):
        #     return {"error": "Se han obtenido temáticas no válidas."}

        # # 5. Mover todas las notas
        # resultados = mover_archivos(clasificaciones)

        # # 6. Devolver los resultados
        # return {
        #     "clasificaciones": clasificaciones,
        #     "movimientos": resultados
        # }
    
    # Prueba manual
    # contenido_prueba = "pollo pescado almendras"

    # resultado = clasificar_contenido(contenido_prueba)

    # print("TEMÁTICA ELEGIDA:", resultado)

# llm = ChatOllama(
#     model="llama3.1:8b",
#     temperature=0,
#     base_url="http://localhost:11434"
# )
    # Conexión MCP por HTTP (devuelve read, write y una función para obtener el session id)
    async with streamable_http_client(MCP_URL) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Importa automáticamente todas las tools que ofrece el servidor
            mcp_tools = await load_mcp_tools(session)
            print("Tools disponibles:", ", ".join(t.name for t in mcp_tools))

            ##prueba temporal
            # for herramienta in mcp_tools:
            #     if herramienta.name == "mover_archivo":
            #         print("Herramienta:", herramienta.name)
            #         print("Argumentos:", herramienta.args)


            # Memoria del agente
            memory = MemorySaver()
            system_prompt = """
            Eres un asistente que usa herramientas MCP para ayudar al usuario. Responde en español.

            Tus funciones principales van a ser crear una nota , copiar una nota de la carpeta de descargas a la carpeta de recepción y leer el contenido de una nota específica.  
            Estos serán los pasos a seguir para cada función:

            Cuando el usuario quiera crear una nota:
            - Pregunta al usuario el nombre de la nota si no lo ha proporcionado.
            - Pregunta al usuario el contenido de la nota si no lo ha proporcionado.
            - Utiliza a la herramienta crear_nota SOLO cuando tengas el nombre y contenido de la nota.
            - Cuando tengas el nombre y contenido de la nota, llama a la herramienta crear_nota con los parámetros nombre_nota y contenido_nota que has obtenido anteriormente.
            - No afirmes que la nota se ha creado si la herramienta no ha realizado la operación correctamente.
            - Interpreta el resultado de la herramienta antes de responder.
            - Si el resultado contiene el texto "Nota Creada exitosamente en la carpeta Recepción.", considera que la creación ha sido correcta.
            
            Cuando el usuario quiera listar las notas por temática:
            - Pregunta al usuario la temática de las notas si no lo ha proporcionado.
            - Si no lo ha indicado , pregúntale qué temática quiere listar
            - No inventes ni supongas una temática
            - Cuando tengas la temática de las notas, llama a la herramienta listar_notas_tematicas con el parámetro temática que has obtenido anteriormente.
            - Utiliza el resultado devuelto por la herramienta para comunicar al ususario la lista de notas encontradas en esa temática.
            - Si la herramienta devuelve un error , comunícaselo al usuario.

            Cuando el usuario quiera almacenar o subir una nota desde la carpeta de descargas a la carpeta de recepción:
            - Pregunta al usuario el nombre de la nota si no lo ha proporcionado.
            - No inventes ni supongas un nombre de nota
            - Cuando tengas el nombre de la nota, llama a la herramienta Copiar_nota con el parámetro nombre_nota que has obtenido anteriormente.
            - No afirmes que la nota se ha copiado si la herramienta no ha realizado la operación correctamente.
            - Interpreta el resultado de la herramienta antes de responder.
            - Si el resultado contiene el texto "Archivo copiado a la carpeta de recepción", considera que la copia ha sido correcta.
            - Si la herramienta devuelve un error , comunícaselo al usuario.

            Cuando el usuario quiera leer una nota:
             - Pregunta al usuario el nombre de la nota si no lo ha proporcionado.
             - No inventes ni supongas un nombre de nota
             - Cuando tengas el nombre de la nota, llama a la herramienta leer_nota con el parámetro nombre_nota que has obtenido anteriormente.
             - Utiliza el resultado devuelto por la herramienta para comunicar al usuario el contenido de la nota.
             - Si la herramienta devuelve un error , comunícaselo al usuario.
            
            Cuando el usuario quiera listar todas las notas de la carpeta de recepción:
            - Llama a la herramienta listar_notas_recepcion.
            - Utiliza el resultado devuelto por la herramienta para comunicar al ususario la lista de notas encontradas en esa carpeta.
            - Si la herramienta devuelve un error , comunícaselo al usuario.


            Cuando el usuario solicite clasificar y mover todas las notas de recepción:

            1. Ejecuta la herramienta `clasificar_y_mover_notas`.

            2. Espera a que termine su ejecución y examina el resultado.

            3. Esta herramienta realiza internamente todo el proceso:
            - Obtiene las notas de la carpeta de recepción.
            - Clasifica cada nota según su contenido en una de las temáticas disponibles: cocina, lectura o deportes.
            - Mueve cada nota a su carpeta temática correspondiente.

            4. Interpreta el resultado devuelto por la herramienta:
            - Comunica las clasificaciones realizadas.
            - Informa del resultado de cada movimiento.
            - Si algún archivo no se ha podido mover, comunica el error correspondiente.
            - Si no hay notas en recepción, informa al usuario.

            IMPORTANTE:
            - Utiliza exclusivamente `clasificar_y_mover_notas` para realizar esta operación.
            - No ejecutes por separado las funciones de clasificación y movimiento.
            - No inventes ni modifiques las clasificaciones devueltas.
            - No afirmes que todos los archivos se han movido correctamente si existen errores.

            """

            app = create_agent(
                llm,
                tools=mcp_tools + [clasificar_y_mover_notas],
                checkpointer=memory,
                system_prompt=system_prompt,
            )

            config = {"configurable": {"thread_id": "mcp_user_1"}}

            while True:
                pregunta = await ainput("Pregunta>>> ")

                if pregunta.lower() in ["salir", "exit", "quit"]:
                    print("Chat terminado")
                    break

                print(f"--- Consulta: {pregunta} ---")
                inputs = {"messages": [("user", pregunta)]}

                async for s in app.astream(inputs, config=config, stream_mode="values"):


                    ##prueba temporal 
                    # print("\n--- HISTORIAL DE MENSAJES ---")

                    # for msg in s["messages"]:
                    #     print(f"\nTipo: {msg.type}")
                    #     print(f"Contenido: {msg.content}")

                    #     if hasattr(msg, "tool_calls") and msg.tool_calls:
                    #         print(f"Llamadas: {msg.tool_calls}")

                    # print("--- FIN DEL HISTORIAL ---")




                    message = s["messages"][-1]
                    # if hasattr(message, "tool_calls") and message.tool_calls:
                    #     print(f"   [MCP: Llamando a {message.tool_calls[0]['name']}...]")
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        for llamada in message.tool_calls:
                            print(f"   [MCP: Llamando a {llamada['name']}]")
                            print(f"   Argumentos enviados: {llamada['args']}")
                
                for msg in s["messages"]:
                    if msg.type == "tool":
                        print(f"\n[RESULTADO MCP]: {msg.content}")

                print(f"\nRESPUESTA FINAL:\n{message.content}")



        

if __name__ == "__main__":
    asyncio.run(main())
