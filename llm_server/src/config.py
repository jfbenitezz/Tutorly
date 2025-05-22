# src/config.py
import os

# --- Directorios Base ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PROJECT_DIR = os.path.join(SCRIPT_DIR, "..")

# --- Configuración del Modelo y Rutas ---
MODEL_FILENAME = "mistral-7b-instruct-v0.2.Q2_K.gguf" 
MODEL_PATH = os.path.join(BASE_PROJECT_DIR, "models", MODEL_FILENAME)
INPUT_FILE_NAME = "transcripcion.txt"
INPUT_FILE_PATH = os.path.join(BASE_PROJECT_DIR, "data", INPUT_FILE_NAME)
OUTPUT_ESQUEMA_FILENAME = "esquema_clase_2.Q4_K_M.txt"
OUTPUT_ESQUEMA_PATH = os.path.join(BASE_PROJECT_DIR, "output", OUTPUT_ESQUEMA_FILENAME)
TEMPLATE_TRANSCRIPCION_FILENAME = "ejemplo_transcripcion_template.txt"
TEMPLATE_TRANSCRIPCION_PATH = os.path.join(BASE_PROJECT_DIR, "templates", TEMPLATE_TRANSCRIPCION_FILENAME) 
OUTPUT_APUNTES_FILENAME = "apuntes_clase_final.md" 
OUTPUT_APUNTES_PATH = os.path.join(BASE_PROJECT_DIR, "output", OUTPUT_APUNTES_FILENAME) 


# --- Configuración del LLM ---
CONTEXT_SIZE = 8192 #16384
MAX_TOKENS_ESQUEMA_PARCIAL = 1024
MAX_TOKENS_ESQUEMA_FUSIONADO = 2048
MAX_TOKENS_APUNTES_POR_SECCION = 1024
N_GPU_LAYERS = 0  # -1 para cargar todas las capas posibles en GPU
N_THREADS = None     # None para que Llama.cpp decida (usualmente óptimo)
LLM_VERBOSE = False
LLM_TEMPERATURE_ESQUEMA = 0.3
LLM_TEMPERATURE_FUSION = 0.2
LLM_TEMPERATURE_APUNTES = 0.4
N_BATCH_LLAMA = 512

# --- Configuración del Mega-Chunking (para generación de esquema si es necesario) ---
MEGA_CHUNK_CONTEXT_FACTOR = 0.7
MEGA_CHUNK_OVERLAP_WORDS = 0