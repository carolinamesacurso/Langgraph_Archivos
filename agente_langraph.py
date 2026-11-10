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
        model='llama3.1:8b-instruct-q4_K_M',
        temperature=0,
        base_url="http://10.42.68.45:11434"
        # base_url="http://localhost:11434",
    )

    # Conexión MCP por HTTP (devuelve read, write y una función para obtener el session id)
    async with streamable_http_client(MCP_URL) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Importa automáticamente todas las tools que ofrece el servidor
            mcp_tools = await load_mcp_tools(session)
            print("Tools disponibles:", ", ".join(t.name for t in mcp_tools))

            # Memoria del agente
            memory = MemorySaver()
            system_prompt = "Eres un asistente que usa herramientas MCP para ayudar al usuario. Responde en español."

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
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        print(f"   [MCP: Llamando a {message.tool_calls[0]['name']}...]")

                print(f"\nRESPUESTA FINAL:\n{message.content}")


if __name__ == "__main__":
    asyncio.run(main())
