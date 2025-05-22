# src/api_main.py
import time
import os
import logging
import re
import tempfile # Para archivos temporales
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

# Importar módulos de tu proyecto
from src import config
from src import utils
from src import llm_processing
from src import prompts

# --- Configuración del Logging ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
# Convertir string a nivel de logging
log_level_int = getattr(logging, LOG_LEVEL, logging.INFO)

log_format = "%(asctime)s [%(levelname)-5s] %(name)-25s %(funcName)-25s L%(lineno)-4d: %(message)s"

# Obtener el logger raíz para configurarlo
root_logger = logging.getLogger()
root_logger.setLevel(log_level_int)

# Limpiar handlers existentes para evitar duplicados si se recarga (con --reload)
if root_logger.hasHandlers():
    root_logger.handlers.clear()

# Handler para la consola
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(log_format))
root_logger.addHandler(stream_handler)

# Opcional: Handler para archivo
# log_file_path = os.path.join(config.BASE_PROJECT_DIR, "output", "api_process.log")
# file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
# file_handler.setFormatter(logging.Formatter(log_format))
# root_logger.addHandler(file_handler)

api_logger = logging.getLogger("api.service") # Logger específico para la lógica de la API

# Crear la aplicación FastAPI
app = FastAPI(
    title="API de Generación de Esquemas y Apuntes de Clases",
    description="Procesa transcripciones para generar esquemas jerárquicos y, opcionalmente, apuntes detallados.",
    version="0.2.0"
)

# --- Funciones Helper para la API ---
def _ensure_output_dir_exists():
    """Asegura que el directorio de salida (para archivos temporales) exista."""
    output_dir = os.path.join(config.BASE_PROJECT_DIR, "output")
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            api_logger.info(f"Directorio de salida creado: {output_dir}")
        except Exception as e:
            api_logger.error(f"No se pudo crear el directorio de salida '{output_dir}': {e}", exc_info=True)
            # Esto podría ser un error crítico para FileResponse si no se puede escribir.
            # Considerar lanzar una excepción aquí si es necesario.

def _cleanup_temp_file(path: str):
    """Función para eliminar un archivo temporal en segundo plano."""
    try:
        if os.path.exists(path):
            os.remove(path)
            api_logger.info(f"Archivo temporal limpiado: {path}")
    except Exception as e:
        api_logger.warning(f"Error limpiando archivo temporal {path}: {e}")


# --- Evento de Inicio de la Aplicación ---
@app.on_event("startup")
async def startup_event():
    api_logger.info("Iniciando API y cargando modelo LLM...")
    utils.crear_directorios_necesarios() # Asegura que data/ y output/ existan
    _ensure_output_dir_exists() # Específicamente para archivos temporales de la API si se guardan ahí
    
    # Cargar modelo con GPU por defecto al inicio. El flag --cpu se maneja por endpoint.
    llm_processing.cargar_modelo_llm(use_cpu_only=False) 
    if llm_processing.llm_instance is None:
        api_logger.error("FALLO CRÍTICO: No se pudo cargar el modelo LLM al iniciar la API.")
    else:
        api_logger.info("Modelo LLM cargado y listo para la API.")

# --- Endpoint para Generar Esquema ---
@app.post("/generar_esquema/", response_class=FileResponse)
async def generar_esquema_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Archivo de transcripción en formato .txt"),
    usar_cpu: bool = Query(False, description="Forzar el uso de CPU para esta solicitud.")
):
    request_start_time = time.time()
    original_filename = file.filename
    api_logger.info(f"Solicitud para generar esquema de: {original_filename}")

    # Manejo de carga de modelo CPU/GPU (simplificado por ahora)
    # La carga inicial en startup usa GPU. Si se pide CPU aquí, idealmente se recargaría.
    # Por ahora, si se pide CPU y el modelo ya está en GPU, se usará GPU.
    # Una solución más robusta requeriría gestionar instancias de modelo separadas o recargas.
    if usar_cpu and not llm_processing.llm_instance.model_params.n_gpu_layers == 0:
        api_logger.warning("Se solicitó CPU, pero el modelo ya está cargado con GPU. Usando GPU.")
        # Aquí iría la lógica de recarga si fuera necesaria y posible sin reiniciar la app.
        # llm_processing.llm_instance = None # Forzar recarga
        # llm_processing.cargar_modelo_llm(use_cpu_only=True)
    
    if llm_processing.llm_instance is None: # Doble chequeo
        api_logger.error("Modelo LLM no está disponible.")
        raise HTTPException(status_code=503, detail="Servicio no disponible: Modelo LLM no cargado.")

    try:
        contenido_bytes = await file.read()
        texto_completo_transcripcion = contenido_bytes.decode("utf-8")
    except Exception as e:
        api_logger.error(f"Error al leer/decodificar archivo '{original_filename}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error al procesar archivo: {e}")

    api_logger.info(f"Transcripción '{original_filename}' leída: {len(texto_completo_transcripcion.split())} palabras.")

    # --- Lógica de Generación de Esquema ---
    esquema_final_texto = None
    try:
        # Análisis de Tokens para Esquema
        prompt_template_base_texto = prompts.PROMPT_GENERAR_ESQUEMA_TEMPLATE.replace("{texto_completo}", "")
        tokens_prompt_base = llm_processing.llm_instance.tokenize(prompt_template_base_texto.encode('utf-8', 'ignore'))
        num_tokens_prompt_base = len(tokens_prompt_base)
        tokens_contenido_transcripcion = llm_processing.llm_instance.tokenize(texto_completo_transcripcion.encode('utf-8', 'ignore'))
        num_tokens_contenido_transcripcion = len(tokens_contenido_transcripcion)
        api_logger.info(f"Tokens para esquema: Base={num_tokens_prompt_base}, Contenido={num_tokens_contenido_transcripcion}")

        tokens_salida_pase_unico = config.MAX_TOKENS_ESQUEMA_FUSIONADO
        max_tokens_para_contenido_en_pase_unico = int(
            (config.CONTEXT_SIZE * config.MEGA_CHUNK_CONTEXT_FACTOR) - num_tokens_prompt_base - tokens_salida_pase_unico
        )
        max_tokens_para_contenido_en_mega_chunk_individual = int(
             (config.CONTEXT_SIZE * config.MEGA_CHUNK_CONTEXT_FACTOR) - num_tokens_prompt_base - config.MAX_TOKENS_ESQUEMA_PARCIAL
        )

        if max_tokens_para_contenido_en_pase_unico <=0 or max_tokens_para_contenido_en_mega_chunk_individual <= 0:
            raise HTTPException(status_code=500, detail="Cálculo de tokens para contenido de esquema resultó no positivo.")

        if num_tokens_contenido_transcripcion <= max_tokens_para_contenido_en_pase_unico:
            api_logger.info("Generando esquema en un solo pase.")
            esquema_final_texto = llm_processing.generar_esquema_de_texto(texto_completo_transcripcion, es_parcial=False)
        else:
            api_logger.info("Generando esquema con mega-chunking.")
            mega_chunks = utils.dividir_en_mega_chunks(
                texto_completo_transcripcion,
                max_tokens_para_contenido_en_mega_chunk_individual,
                config.MEGA_CHUNK_OVERLAP_WORDS, # Actualmente 0
                llm_tokenizer_instance=llm_processing.llm_instance
            )
            if not mega_chunks: raise HTTPException(status_code=500, detail="No se generaron mega-chunks.")
            
            esquemas_parciales = []
            for i, mega_chunk_texto in enumerate(mega_chunks):
                esquema_parcial = llm_processing.generar_esquema_de_texto(
                    mega_chunk_texto, es_parcial=True, chunk_num=i + 1, total_chunks=len(mega_chunks)
                )
                if esquema_parcial: esquemas_parciales.append(esquema_parcial)
            
            if not esquemas_parciales: raise HTTPException(status_code=500, detail="No se generaron esquemas parciales.")
            esquema_final_texto = llm_processing.fusionar_esquemas(esquemas_parciales)

        if not esquema_final_texto or not esquema_final_texto.strip():
            raise HTTPException(status_code=500, detail="Fallo en la generación del esquema final.")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e_esquema:
        api_logger.error(f"Error durante la generación del esquema para '{original_filename}': {e_esquema}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al generar el esquema: {str(e_esquema)}")

    # Guardar en archivo temporal y devolver FileResponse
    nombre_base_salida = os.path.splitext(original_filename)[0]
    
    # Usar NamedTemporaryFile para manejo automático de la eliminación (con delete=False inicialmente)
    try:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt", encoding="utf-8", dir=os.path.join(config.BASE_PROJECT_DIR, "output")) as tmp_file:
            tmp_file.write(esquema_final_texto)
            temp_file_path = tmp_file.name
        api_logger.info(f"Esquema temporal para '{original_filename}' guardado en: {temp_file_path}")
        
        background_tasks.add_task(_cleanup_temp_file, temp_file_path)
        
        api_logger.info(f"Devolviendo archivo de esquema: {nombre_base_salida}_esquema.txt")
        processing_time = round(time.time() - request_start_time, 2)
        api_logger.info(f"Tiempo total para generar esquema de '{original_filename}': {processing_time} seg.")

        return FileResponse(
            path=temp_file_path,
            filename=f"{nombre_base_salida}_esquema.txt",
            media_type='text/plain'
        )
    except Exception as e_file_resp:
        api_logger.error(f"Error al preparar FileResponse para esquema de '{original_filename}': {e_file_resp}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al servir el archivo de esquema: {str(e_file_resp)}")


# --- Endpoint para Generar Apuntes ---
@app.post("/generar_apuntes/", response_class=FileResponse)
async def generar_apuntes_endpoint(
    background_tasks: BackgroundTasks,
    transcripcion_file: UploadFile = File(..., description="Archivo de transcripción original (.txt)"),
    esquema_texto: str = Form(..., description="Texto completo del esquema generado previamente."),
    usar_cpu: bool = Query(False, description="Forzar el uso de CPU para esta solicitud.")
):
    request_start_time = time.time()
    original_transcripcion_filename = transcripcion_file.filename
    api_logger.info(f"Solicitud para generar apuntes basada en esquema para: {original_transcripcion_filename}")

    # Similar manejo de CPU que en el endpoint de esquema
    if usar_cpu and not llm_processing.llm_instance.model_params.n_gpu_layers == 0:
        api_logger.warning("Se solicitó CPU, pero el modelo ya está cargado con GPU. Usando GPU.")
        # Lógica de recarga iría aquí
    
    if llm_processing.llm_instance is None:
        api_logger.error("Modelo LLM no está disponible.")
        raise HTTPException(status_code=503, detail="Servicio no disponible: Modelo LLM no cargado.")

    try:
        contenido_bytes_transcripcion = await transcripcion_file.read()
        texto_completo_transcripcion = contenido_bytes_transcripcion.decode("utf-8")
    except Exception as e:
        api_logger.error(f"Error al leer/decodificar archivo de transcripción '{original_transcripcion_filename}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error al procesar archivo de transcripción: {e}")

    if not esquema_texto or not esquema_texto.strip():
        raise HTTPException(status_code=400, detail="El texto del esquema no puede estar vacío.")

    # --- Lógica de Generación de Apuntes ---
    apuntes_texto_final_md = None
    try:
        api_logger.info("Dividiendo el esquema en secciones para generar apuntes.")
        secciones_del_esquema = re.split(r"\n(?=\d+\.\s)", esquema_texto.strip())
        secciones_del_esquema = [s.strip() for s in secciones_del_esquema if s.strip()]
        
        apuntes_completos_md_list = []
        if not secciones_del_esquema and esquema_texto.strip():
            apuntes_para_seccion_unica = llm_processing.generar_apuntes_por_seccion(
                esquema_texto, texto_completo_transcripcion, 1, 1
            )
            if apuntes_para_seccion_unica:
                apuntes_completos_md_list.append(f"## Resumen General de la Clase\n{apuntes_para_seccion_unica.strip()}")
        elif secciones_del_esquema:
            for i, seccion_esq_texto in enumerate(secciones_del_esquema):
                apuntes_para_esta_seccion = llm_processing.generar_apuntes_por_seccion(
                    seccion_esq_texto, texto_completo_transcripcion, i + 1, len(secciones_del_esquema)
                )
                if apuntes_para_esta_seccion:
                    apuntes_completos_md_list.append(apuntes_para_esta_seccion.strip())
        
        if apuntes_completos_md_list:
            nombre_base_salida = os.path.splitext(original_transcripcion_filename)[0]
            apuntes_texto_final_md = f"# Guía de Estudio Detallada: {nombre_base_salida}\n\n" + "\n\n".join(apuntes_completos_md_list)
        else:
            api_logger.warning("No se generó contenido para los apuntes.")
            raise HTTPException(status_code=500, detail="No se pudo generar contenido para los apuntes.")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e_apuntes:
        api_logger.error(f"Error durante la generación de apuntes para '{original_transcripcion_filename}': {e_apuntes}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al generar apuntes: {str(e_apuntes)}")

    # Guardar en archivo temporal y devolver FileResponse
    nombre_base_salida = os.path.splitext(original_transcripcion_filename)[0]
    try:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".md", encoding="utf-8", dir=os.path.join(config.BASE_PROJECT_DIR, "output")) as tmp_file:
            tmp_file.write(apuntes_texto_final_md)
            temp_file_path_apuntes = tmp_file.name
        api_logger.info(f"Apuntes temporales para '{original_transcripcion_filename}' guardados en: {temp_file_path_apuntes}")

        background_tasks.add_task(_cleanup_temp_file, temp_file_path_apuntes)

        api_logger.info(f"Devolviendo archivo de apuntes: {nombre_base_salida}_apuntes.md")
        processing_time = round(time.time() - request_start_time, 2)
        api_logger.info(f"Tiempo total para generar apuntes de '{original_transcripcion_filename}': {processing_time} seg.")
        
        return FileResponse(
            path=temp_file_path_apuntes,
            filename=f"{nombre_base_salida}_apuntes.md",
            media_type='text/markdown'
        )
    except Exception as e_file_resp_apuntes:
        api_logger.error(f"Error al preparar FileResponse para apuntes de '{original_transcripcion_filename}': {e_file_resp_apuntes}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al servir el archivo de apuntes: {str(e_file_resp_apuntes)}")

# ... (your existing imports and code)

@app.get("/list_schemas/")
async def list_schemas():
    """List all schema files in the output directory"""
    output_dir = Path(config.BASE_PROJECT_DIR) / "output"
    schema_files = []
    
    try:
        for file in output_dir.glob("*.txt"):
            schema_files.append({
                "filename": file.name,
                "path": str(file),
                "size": file.stat().st_size,
                "last_modified": file.stat().st_mtime
            })
        return JSONResponse({"schemas": schema_files})
    except Exception as e:
        api_logger.error(f"Error listing schema files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error accessing output directory")

@app.get("/get_schema/{filename}")
async def get_schema_text(filename: str):
    """Retrieve the text content of a specific schema file by filename"""
    # Security check - prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    output_dir = Path(config.BASE_PROJECT_DIR) / "output"
    file_path = output_dir / filename
    
    try:
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Schema file not found")
            
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Not a valid file")
            
        # Optional: Verify it's actually a schema file
        if not filename.endswith("_esquema.txt"):
            api_logger.warning(f"File {filename} may not be a schema file")
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return JSONResponse({"schema": content})
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text")
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Error reading schema file {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error reading file content")
# Para ejecutar desde la raíz del proyecto: uvicorn src.api_main:app --reload