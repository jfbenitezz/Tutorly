# src/utils.py
import os
import time
from contextlib import contextmanager
import logging
from src import config

logger = logging.getLogger(__name__)

def format_duration(seconds):
    if seconds < 0: return "N/A (tiempo negativo)"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    if minutes == 0: return f"{remaining_seconds:.2f} seg"
    return f"{minutes} min {remaining_seconds:.2f} seg"

@contextmanager
def timed_phase(phase_name):
    logger.info(f"--- Iniciando Fase: {phase_name} ---")
    start_time = time.time()
    yield
    duration = time.time() - start_time
    logger.info(f"--- Fin Fase: {phase_name} (Duración: {format_duration(duration)}) ---")

def _leer_contenido_template(template_path):
    # Esta función necesita config para TEMPLATE_TRANSCRIPCION_PATH
    # Si config solo se usa para eso, podríamos pasar la ruta directamente
    # o mantener la importación de config.
    # Por ahora, asumimos que config.py se importa en los módulos que lo necesitan.
    from src import config # Importar config aquí si es necesario solo para esta función
    try:
        with open(template_path, 'r', encoding='utf-8') as f_template:
            return f_template.read()
    except FileNotFoundError:
        logger.error(f"Archivo template no encontrado en: {template_path}")
        return None
    except Exception as e_template:
        logger.error(f"Error al leer el archivo template '{template_path}': {e_template}", exc_info=True)
        return None

def leer_archivo(ruta_archivo):
    from src import config # Importar config aquí
    logger.debug(f"Intentando leer archivo: {ruta_archivo}")
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Archivo '{ruta_archivo}' leído exitosamente ({len(content)} caracteres).")
            return content
    except FileNotFoundError:
        logger.error(f"Archivo no encontrado en {ruta_archivo}")
        if ruta_archivo == config.INPUT_FILE_PATH:
            logger.info(f"Creando un archivo de ejemplo '{config.INPUT_FILE_NAME}' en la carpeta 'data' "
                        f"usando el template de '{config.TEMPLATE_TRANSCRIPCION_PATH}'. Por favor, edítalo si es necesario.")
            ejemplo_txt = _leer_contenido_template(config.TEMPLATE_TRANSCRIPCION_PATH)
            if ejemplo_txt is None:
                logger.error("No se pudo leer el contenido del template. No se creará el archivo de ejemplo.")
                return None
            try:
                os.makedirs(os.path.dirname(config.INPUT_FILE_PATH), exist_ok=True)
                with open(config.INPUT_FILE_PATH, 'w', encoding='utf-8') as f_output:
                     f_output.write(ejemplo_txt)
                logger.info(f"Archivo de ejemplo '{config.INPUT_FILE_NAME}' creado exitosamente en '{config.INPUT_FILE_PATH}'.")
                return ejemplo_txt
            except Exception as e_create:
                logger.error(f"No se pudo crear el archivo de ejemplo en '{config.INPUT_FILE_PATH}': {e_create}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error inesperado al leer el archivo '{ruta_archivo}': {e}", exc_info=True)
        return None

def guardar_texto_a_archivo(texto_generado, ruta_archivo, descripcion_archivo="archivo"):
    if texto_generado:
        logger.info(f"Guardando {descripcion_archivo} en: {ruta_archivo}")
        try:
            os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                f.write(texto_generado)
            logger.info(f"¡{descripcion_archivo.capitalize()} guardado exitosamente!")
        except Exception as e:
            logger.error(f"Al guardar {descripcion_archivo} en '{ruta_archivo}': {e}", exc_info=True)
    else:
        logger.warning(f"No se pudo guardar {descripcion_archivo} en '{ruta_archivo}' (contenido vacío o error previo).")

def crear_directorios_necesarios():
    from src import config # Importar config aquí
    logger.debug(f"Asegurando que los directorios base existan: output y data en {config.BASE_PROJECT_DIR}")
    try:
        os.makedirs(os.path.join(config.BASE_PROJECT_DIR, "output"), exist_ok=True)
        os.makedirs(os.path.join(config.BASE_PROJECT_DIR, "data"), exist_ok=True)
        logger.debug("Directorios 'output' y 'data' listos.")
    except Exception as e:
        logger.error(f"No se pudieron crear los directorios necesarios: {e}", exc_info=True)


def dividir_en_mega_chunks(texto_completo, max_tokens_contenido_chunk, overlap_palabras, llm_tokenizer_instance):
    """
    Divide el texto en mega-chunks, respetando un límite de tokens para el contenido de cada chunk.
    Intenta hacer los chunks lo más grandes posible (cercanos a max_tokens_contenido_chunk)
    y aplica el overlap en palabras.
    """
    if not llm_tokenizer_instance:
        logger.error("(mega-chunks): Se requiere una instancia de tokenizador LLM.")
        return []
    if max_tokens_contenido_chunk <= 0:
        logger.error(f"(mega-chunks): max_tokens_contenido_chunk ({max_tokens_contenido_chunk}) debe ser positivo.")
        return []
    if overlap_palabras < 0:
        logger.warning("(mega-chunks): overlap_palabras es negativo, se usará 0.")
        overlap_palabras = 0

    palabras_originales = texto_completo.split()
    if not palabras_originales:
        logger.warning("(mega-chunks): Texto a dividir está vacío.")
        return []

    mega_chunks_finales = []
    indice_palabra_actual = 0
    num_palabras_total = len(palabras_originales)

    # Heurística para la ventana inicial de palabras:
    # Asumimos que, en promedio, un token podría ser entre 0.5 y 4 palabras.
    # Para ser generosos y capturar el límite superior, podemos multiplicar max_tokens por un factor grande (ej. 3 o 4).
    # O, de forma más simple, tomar una porción significativa del texto restante.
    # Esta ventana solo sirve como punto de partida para la reducción.
    palabras_ventana_inicial_max = max_tokens_contenido_chunk * 4 # Estimación muy laxa (ej. 4 palabras por token como máximo)
    palabras_ventana_inicial_max = max(palabras_ventana_inicial_max, overlap_palabras + 50) # Asegurar que sea suficientemente grande

    logger.info(f"(mega-chunks): Dividiendo texto. Objetivo por chunk: <= {max_tokens_contenido_chunk} tokens. "
                f"Overlap palabras: {overlap_palabras}. Ventana inicial palabras MÁXIMA (est.): {palabras_ventana_inicial_max}.")

    iteracion_chunk_num = 0
    while indice_palabra_actual < num_palabras_total:
        iteracion_chunk_num += 1
        logger.debug(f"[Chunk Iter {iteracion_chunk_num}] Iniciando en palabra índice: {indice_palabra_actual}")

        palabras_restantes_en_texto = num_palabras_total - indice_palabra_actual
        
        # La ventana de palabras candidatas no puede ser mayor que las palabras restantes
        # ni mayor que nuestra estimación laxa de ventana máxima.
        palabras_a_considerar_en_ventana = min(palabras_restantes_en_texto, palabras_ventana_inicial_max)
        
        if palabras_a_considerar_en_ventana <= 0 : # No quedan palabras suficientes para formar un chunk
             logger.debug(f"[Chunk Iter {iteracion_chunk_num}] No quedan suficientes palabras para considerar ({palabras_a_considerar_en_ventana}). Finalizando chunking.")
             break

        # Tomar las palabras candidatas
        palabras_candidatas = palabras_originales[indice_palabra_actual : indice_palabra_actual + palabras_a_considerar_en_ventana]
        logger.debug(f"[Chunk Iter {iteracion_chunk_num}] Ventana palabras candidatas inicial: {len(palabras_candidatas)}")
        
        texto_chunk_final = ""
        num_tokens_chunk_final = 0
        palabras_en_chunk_final = 0
        
        # Reducir el chunk candidato hasta que quepa en tokens
        while palabras_candidatas:
            texto_intento = " ".join(palabras_candidatas)
            if not texto_intento.strip():
                palabras_candidatas = [] # Evitar bucle si se vacía
                continue
            
            try:
                tokens_intento = llm_tokenizer_instance.tokenize(texto_intento.encode('utf-8', 'ignore'))
                num_tokens_intento = len(tokens_intento)
            except Exception as e_tok:
                logger.warning(f"(mega-chunks) Error al tokenizar candidato: '{texto_intento[:30]}...'. Error: {e_tok}. Acortando candidato.")
                if len(palabras_candidatas) > 1 :
                    palabras_candidatas.pop() # Quitar palabra y reintentar
                    continue
                else: # Falló con una palabra, no se puede acortar más
                    palabras_candidatas = [] 
                    break

            if num_tokens_intento <= max_tokens_contenido_chunk:
                texto_chunk_final = texto_intento
                num_tokens_chunk_final = num_tokens_intento
                palabras_en_chunk_final = len(palabras_candidatas)
                logger.debug(f"[Chunk Iter {iteracion_chunk_num}] Chunk válido encontrado: {palabras_en_chunk_final} palabras, {num_tokens_chunk_final} tokens.")
                break # Encontramos el chunk más grande (o igual) que cabe
            else:
                # Excede tokens, quitar la última palabra y reintentar
                if len(palabras_candidatas) > 1:
                    palabras_candidatas.pop()
                else: # Una sola palabra excede el límite
                    logger.warning(f"(mega-chunks): Palabra única '{palabras_candidatas[0][:50]}...' ({num_tokens_intento} tokens) "
                                   f"excede límite de {max_tokens_contenido_chunk} tokens. Será omitida en esta iteración.")
                    palabras_candidatas = [] # Vaciar para indicar que no se formó chunk
                    break 
        
        if texto_chunk_final:
            mega_chunks_finales.append(texto_chunk_final)
            logger.debug(f"  Mega-chunk Creado ({iteracion_chunk_num}): {palabras_en_chunk_final} palabras, {num_tokens_chunk_final} tokens. "
                         f"Inició en palabra {indice_palabra_actual}.")
            
            avance_palabras = max(1, palabras_en_chunk_final - overlap_palabras)
            # Asegurar que el avance no nos saque de los límites si el overlap es muy grande
            # o el chunk es muy pequeño.
            if indice_palabra_actual + avance_palabras > num_palabras_total:
                avance_palabras = num_palabras_total - indice_palabra_actual # Avanzar solo lo que queda
            
            indice_palabra_actual += avance_palabras
            logger.debug(f"  Nuevo índice_palabra_actual: {indice_palabra_actual} (avance: {avance_palabras})")

        elif indice_palabra_actual < num_palabras_total: 
            logger.warning(f"(mega-chunks): No se pudo formar un chunk válido en iteración {iteracion_chunk_num} "
                           f"(índice palabra: {indice_palabra_actual}). Avanzando 1 palabra para evitar bucle.")
            indice_palabra_actual += 1 
        else: 
            break # Salir del bucle principal si no hay progreso y no quedan palabras

    if not mega_chunks_finales and texto_completo:
        logger.warning("(mega-chunks): No se generó ningún mega-chunk, pero el texto original no estaba vacío. "
                       "Esto podría indicar que max_tokens_contenido_chunk es demasiado pequeño o hay problemas con la tokenización.")

    logger.info(f"(mega-chunks): Texto dividido en {len(mega_chunks_finales)} mega-chunks.")
    return mega_chunks_finales