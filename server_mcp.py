from mcp.server.fastmcp import FastMCP
import os

# --- CONFIGURACIÓN ---
HOST = "127.0.0.1"   # usa "0.0.0.0" si quieres acceder desde otra máquina
PORT = 8000
#path de ubuntu 
NOTES_DIR = "/home/carolinamesamartine/notasPruebas/misnotas" #temáticas dir
RECEPCION_DIR = "/home/carolinamesamartine/Escritorio/notasPruebas/recepcion" #recepcion dir 
DESCARGAS_DIR = "/home/carolinamesamartine/notasPruebas/descargas" #descargas dir 
TEMÁTICAS= ["cocina", "deporte", "lectura"]
os.makedirs(NOTES_DIR, exist_ok=True)
os.makedirs(RECEPCION_DIR, exist_ok=True)
os.makedirs(DESCARGAS_DIR, exist_ok=True)

mcp = FastMCP("Gestor de Notas", host=HOST, port=PORT)


@mcp.tool()
def listar_notas_tematicas(nombre_tema: str) -> str:
    """Lista todos los archivos de texto disponibles en la carpeta nombrada igual que la temática dada por el usuario , se buscarán estas carpetas dentro de la carpeta de notas."""
    base = os.path.realpath(NOTES_DIR)
    dirpath = os.path.realpath(os.path.join(base, nombre_tema))

    if not os.path.isdir(dirpath):
            return "Error: La carpeta de la temática no existe."
    try:
        files = sorted(os.listdir(dirpath))
        return "\n".join(files) if files else "No hay notas aún en esa temática."
    except Exception as e:
        return f"Error al listar notas: {str(e)}"
    
@mcp.tool()
def crear_nota(nombre_nota: str,contenido_nota: str) -> str:
    """Crea una nota como un archivo .txt para guardarlo en la carpeta de recepción ."""
    base = os.path.realpath(RECEPCION_DIR)

    if not os.path.isdir(base):
            return "Error: La carpeta no existe."
    try:
        ruta_completa = os.path.join(base, f"{nombre_nota}.txt")

        with open(ruta_completa, "w", encoding="utf-8") as f:
            f.write(contenido_nota)

        return "Nota Creada exitosamente en la carpeta Recepción."
    except Exception as e:
        return f"Error al crear la nota: {str(e)}"

@mcp.tool()
def Copiar_nota(nombre_nota: str) -> str:
    """Copia un archivo indicado por el usuario de la carpeta local de descargas a la carpeta recepción."""
    base = os.path.realpath(DESCARGAS_DIR)
    destino = os.path.realpath(RECEPCION_DIR)

    archivo_origen = os.path.realpath(os.path.join(base, nombre_nota))

    # Comprobar que el archivo está dentro de la carpeta de notas
    if os.path.commonpath([base, archivo_origen]) != base:
        return "Error: Acceso denegado a archivos fuera del directorio de notas."

    if not os.path.isfile(archivo_origen):
        return "Error: La nota no existe."
    
    try:
        ruta_completa_destino = os.path.join(destino, f"{nombre_nota}.txt")

        with open(archivo_origen, "r", encoding="utf-8") as f:
            contenido = f.read()
        
        with open(ruta_completa_destino, "w", encoding="utf-8") as f:
            f.write(contenido)

        return "Archivo copiado a la carpeta de recepción"
    except Exception as e:
        return f"Error copiando el archivo: {str(e)}"

    
   

# @mcp.tool()
# def leer_nota(nombre_archivo: str) -> str:
#     """Lee el contenido de una nota específica."""
#     base = os.path.realpath(NOTES_DIR)
#     filepath = os.path.realpath(os.path.join(base, nombre_archivo))

#     # Comprobar que el archivo está dentro de la carpeta de notas
#     if os.path.commonpath([base, filepath]) != base:
#         return "Error: Acceso denegado a archivos fuera del directorio de notas."

#     if not os.path.isfile(filepath):
#         return "Error: La nota no existe."

#     try:
#         with open(filepath, "r", encoding="utf-8") as f:
#             return f.read()
#     except Exception as e:
#         return f"Error leyendo el archivo: {str(e)}"


if __name__ == "__main__":
    # Streamable HTTP: el endpoint queda en http://HOST:PORT/mcp
    print(f"Servidor MCP escuchando en http://{HOST}:{PORT}/mcp")
    mcp.run(transport="streamable-http")


#notas
#            os.makedirs(dirpath)
 # # Verificar si el archivo de origen existe antes de copiar
    # if os.path.exists(origen):
    #     with open(origen, "rb") as f_origen: #leer la nota
    #         contenido = f_origen.read()
            
    #     with open(destino, "wb") as f_destino: #escribir de nuevo la nota
    #         f_destino.write(contenido)
            
    #     print("Archivo copiado con éxito usando os.")
    # else:
    #     print(f"Error: El archivo '{origen}' no existe.")



    # base = os.path.realpath(RECEPCION_DIR)

    # if not os.path.isdir(base):
    #         return "Error: La carpeta no existe."
    # try:
    #     ruta_completa = os.path.join(base, f"{nombre_nota}.txt")

    #     with open(ruta_completa, "w", encoding="utf-8") as f:
    #         f.write(contenido_nota)

    #     return "Nota Creada exitosamente en la carpeta Recepción."
    # except Exception as e:
    #     return f"Error al crear la nota: {str(e)}"