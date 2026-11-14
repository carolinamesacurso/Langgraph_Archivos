import asyncio
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# --- CONFIGURACIÓN DEL SERVIDOR MCP (HTTP) ---
# El servidor debe estar arrancado antes: python server_http.py
MCP_URL = "http://127.0.0.1:8000/mcp"


async def ainput(prompt: str) -> str:
    # Permite que el loop de asyncio siga corriendo mientras el usuario escribe
    return await asyncio.to_thread(input, prompt)


async def main():
    # Configurar el LLM
    llm = ChatOllama(
        # model='llama3.1:8b-instruct-q4_K_M',
        model='llama3.1:8b',
        temperature=0,
        base_url="http://localhost:11434"
        # base_url="http://10.42.68.45:11434"
        # base_url="http://127.0.0.1:11434",
    )
    
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
            """

            app = create_agent(
                llm,
                tools=mcp_tools,
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
