# src/test_llm.py

from llama_cpp import Llama
import os
import time # Para medir el tiempo de carga

# --- Configuración ---
# Asegúrate de que este nombre coincida EXACTAMENTE con tu archivo .gguf descargado
MODEL_FILENAME = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"  # CAMBIA ESTO si tu archivo se llama diferente

# Construye la ruta al modelo asumiendo que este script está en src/ y models/ está al mismo nivel que src/
# __file__ es la ruta de este script (src/test_llm.py)
# os.path.dirname(__file__) es la ruta de la carpeta src/
# os.path.abspath(...) obtiene la ruta absoluta
# os.path.join(...) une las partes para formar la ruta completa al modelo
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "..", "models", MODEL_FILENAME)

CONTEXT_SIZE = 4096  # Tamaño del contexto, ajusta según tu modelo y memoria (Mistral 7B suele soportar 8k o 32k, pero 4k es un inicio seguro)
MAX_TOKENS_TO_GENERATE = 100 # Cuántos tokens generar en la respuesta de prueba
N_GPU_LAYERS = -1 # -1 para intentar usar GPU para todo, 0 para usar solo CPU
N_THREADS = None # None usa un número óptimo de hilos CPU, puedes ajustarlo si es necesario (ej. 4)

# --- Cargar Modelo ---
print(f"Intentando cargar modelo desde: {MODEL_PATH}")

# Verifica si el archivo del modelo existe antes de intentar cargarlo
if not os.path.exists(MODEL_PATH):
    print(f"ERROR: No se encontró el archivo del modelo en la ruta especificada: {MODEL_PATH}")
    print("Verifica que el nombre del archivo en MODEL_FILENAME sea correcto y que el archivo esté en la carpeta 'models'.")
    exit() # Sale del script si no encuentra el modelo

try:
    start_time = time.time()
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=CONTEXT_SIZE,       # Tamaño de la ventana de contexto
        n_threads=N_THREADS,      # Número de hilos CPU a usar
        n_gpu_layers=N_GPU_LAYERS # Número de capas a descargar en la GPU (-1 = intentar todas)
    )
    end_time = time.time()
    print(f"Modelo cargado exitosamente en {end_time - start_time:.2f} segundos.")

    # --- Prueba de Inferencia Simple ---
    prompt = "Explica brevemente qué es la Programación Lineal."
    print(f"\nEnviando prompt al LLM:")
    print(f"'{prompt}'")

    start_time = time.time()
    output = llm(
        prompt,
        max_tokens=MAX_TOKENS_TO_GENERATE, # Límite de tokens a generar
        stop=["\n", "Q:", "User:"],       # Palabras/tokens donde detener la generación
        echo=False                        # No repetir el prompt en la salida
    )
    end_time = time.time()

    print(f"\nRespuesta del LLM (generada en {end_time - start_time:.2f} segundos):")
    # Extrae el texto generado de la estructura de datos que devuelve llama_cpp
    generated_text = output['choices'][0]['text'].strip()
    print(generated_text)

except Exception as e:
    print(f"\nERROR: Ocurrió un problema durante la carga o inferencia del modelo.")
    print(e)
    print("\nPosibles causas:")
    print("- Asegúrate de haber instalado 'llama-cpp-python' correctamente (con las herramientas de compilación C++).")
    print("- Verifica que la ruta al modelo (MODEL_PATH) sea correcta.")
    print("- Tu PC podría no tener suficiente RAM o VRAM para cargar el modelo con la configuración actual (intenta reducir n_gpu_layers si usas GPU, o usa un modelo más pequeño).")
    print("- El archivo del modelo podría estar corrupto.")