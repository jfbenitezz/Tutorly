# src/llm_processing.py
from llama_cpp import Llama
import os
import time
import re
import logging # <--- Importar logging
from src import config
from src import prompts

logger = logging.getLogger(__name__)
llm_instance = None # Esta será la instancia global del modelo cargado

def cargar_modelo_llm(use_cpu_only=False): # <--- Añadir parámetro use_cpu_only
    global llm_instance
    if llm_instance is not None:
        logger.info("Modelo LLM ya está cargado.")
        return llm_instance

    logger.info(f"Cargando modelo desde: {config.MODEL_PATH}")
    if not os.path.exists(config.MODEL_PATH):
        logger.critical(f"No se encontró el archivo del modelo en {config.MODEL_PATH}")
        return None

    n_gpu_layers_to_use = config.N_GPU_LAYERS
    if use_cpu_only:
        logger.info("Forzando uso de CPU: n_gpu_layers se establecerá en 0.")
        n_gpu_layers_to_use = 0
    else:
        logger.info(f"Usando n_gpu_layers de configuración: {config.N_GPU_LAYERS}")
        
    try:
        start_time_carga = time.time()
        llm_instance = Llama(
            model_path=config.MODEL_PATH,
            n_ctx=config.CONTEXT_SIZE,
            n_threads=config.N_THREADS,
            n_gpu_layers=n_gpu_layers_to_use, # <--- Usar la variable ajustada
            n_batch=config.N_BATCH_LLAMA,
            verbose=config.LLM_VERBOSE,
            seed=42, 
        )
        end_time_carga = time.time()
        logger.info(f"Modelo LLM cargado exitosamente en {end_time_carga - start_time_carga:.2f} segundos.")
        if use_cpu_only:
            logger.info("Modelo cargado en modo CPU (n_gpu_layers=0).")
        elif n_gpu_layers_to_use > 0 :
             logger.info(f"Modelo cargado con {n_gpu_layers_to_use} capas en GPU.")
        else: # n_gpu_layers_to_use es 0 (o negativo si config.N_GPU_LAYERS era negativo y no se forzó CPU)
             logger.info(f"Modelo cargado con {n_gpu_layers_to_use} capas en GPU (podría ser CPU si es 0 o negativo y no hay GPU).")

        return llm_instance
    except Exception as e:
        logger.critical(f"Al cargar el modelo LLM: {e}", exc_info=True)
        logger.info("Posibles causas: CONTEXT_SIZE, archivo corrupto, Llama.cpp sin soporte GPU.")
        llm_instance = None
        return None

def _llamar_al_llm(prompt_texto, max_tokens_salida, temperatura, descripcion_tarea, stop_sequences=None):
    if llm_instance is None:
        logger.critical(f"Modelo LLM no cargado. No se puede procesar '{descripcion_tarea}'.")
        return None, "llm_not_loaded", {}

    num_tokens_prompt_reales = 0
    try:
        if llm_instance:
            num_tokens_prompt_reales = len(llm_instance.tokenize(prompt_texto.encode('utf-8', 'ignore')))
        else:
            logger.warning(f"llm_instance no disponible para tokenizar prompt para '{descripcion_tarea}' (conteo previo).")
    except Exception as e_tok:
        logger.warning(f"No se pudo tokenizar el prompt para '{descripcion_tarea}' para conteo previo: {e_tok}")

    logger.info(f"Enviando prompt al LLM para '{descripcion_tarea}' (~{num_tokens_prompt_reales} tokens), "
                f"max_tokens_out: {max_tokens_salida}, temp: {temperatura}.")

    if num_tokens_prompt_reales > 0 and \
       (num_tokens_prompt_reales + max_tokens_salida) > config.CONTEXT_SIZE * 0.98:
        logger.warning(f"El prompt actual ({num_tokens_prompt_reales} tokens) + salida ({max_tokens_salida}) "
                       f"podría exceder CONTEXT_SIZE ({config.CONTEXT_SIZE}). Total: {num_tokens_prompt_reales + max_tokens_salida}")
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Prompt para '{descripcion_tarea}':\n'''\n{prompt_texto[:500]}...\n'''")
    
    start_time_llm = time.time()
    try:
        output = llm_instance(
            prompt_texto,
            max_tokens=max_tokens_salida,
            stop=stop_sequences,
            echo=False,
            temperature=temperatura,
            seed=42
        )
        
        end_time_llm = time.time()
        processing_time = end_time_llm - start_time_llm

        texto_generado = ""
        finish_reason = "desconocido"
        tokens_generados = 0
        tokens_prompt_from_usage = 0

        if output and 'choices' in output and len(output['choices']) > 0:
            texto_generado = output['choices'][0]['text'].strip()
            finish_reason = output['choices'][0].get('finish_reason', 'desconocido')
            if finish_reason is None: finish_reason = "completed_unknown"
            
            usage_stats = output.get('usage', {})
            tokens_generados = usage_stats.get('completion_tokens', 0)
            if tokens_generados == 0 and texto_generado:
                try:
                    tokens_generados = len(llm_instance.tokenize(texto_generado.encode('utf-8', 'ignore')))
                except Exception as e:
                     logger.debug(f"No se pudo tokenizar el texto generado para fallback: {e}")

            tokens_prompt_from_usage = usage_stats.get('prompt_tokens', 0)
        
        else:
            logger.warning(f"La salida del LLM para '{descripcion_tarea}' fue inesperada o vacía. Output: {output}")
            return None, "empty_or_invalid_llm_output", {"tokens_prompt": num_tokens_prompt_reales}

        final_tokens_prompt_stat = tokens_prompt_from_usage
        if final_tokens_prompt_stat == 0:
            if num_tokens_prompt_reales > 0:
                final_tokens_prompt_stat = num_tokens_prompt_reales
            elif llm_instance: 
                try:
                    final_tokens_prompt_stat = len(llm_instance.tokenize(prompt_texto.encode('utf-8', 'ignore')))
                except Exception:
                    pass 

        tokens_por_segundo = 0
        if processing_time > 0 and tokens_generados > 0:
            tokens_por_segundo = tokens_generados / processing_time
        
        stats = {
            "tokens_prompt": final_tokens_prompt_stat,
            "tokens_generados": tokens_generados,
            "processing_time_seconds": processing_time,
            "tokens_por_segundo": tokens_por_segundo
        }

        logger.info(f"LLM Task '{descripcion_tarea}' completada en {processing_time:.2f} seg.")
        logger.info(f"  Stats: Prompt Tokens: {stats['tokens_prompt']}, Tokens Generados: {tokens_generados}, Tasa: {tokens_por_segundo:.2f} tokens/seg.")
        logger.info(f"  Finish Reason: {finish_reason}")

        if finish_reason == 'length':
            logger.warning(f"¡CORTE! La generación para '{descripcion_tarea}' se detuvo por max_tokens ({max_tokens_salida}).")
            if logger.isEnabledFor(logging.DEBUG):
                 logger.debug(f"  Últimos 150 caracteres generados: '...{texto_generado[-150:]}'")
        elif finish_reason not in ['stop', 'eos_token', 'completed_unknown'] and \
             (stop_sequences is None or finish_reason not in stop_sequences):
             logger.warning(f"Razón de finalización inusual para '{descripcion_tarea}': {finish_reason}")
        
        return texto_generado, finish_reason, stats

    except Exception as e:
        logger.error(f"Durante la llamada al LLM para '{descripcion_tarea}': {e}", exc_info=True)
        return None, f"exception_during_llm_call: {str(e)}", {"tokens_prompt": num_tokens_prompt_reales}


def generar_esquema_de_texto(texto_para_esquema, es_parcial=False, chunk_num=None, total_chunks=None):

    if es_parcial:
        num_str = str(chunk_num) if chunk_num is not None else "?"
        total_str = str(total_chunks) if total_chunks is not None else "?"
        descripcion_proceso_base = f"Esquema Parcial (Mega-Chunk {num_str}/{total_str})"
        prompt_final_esquema = prompts.PROMPT_GENERAR_ESQUEMA_PARCIAL_TEMPLATE.format(
            texto_fragmento=texto_para_esquema,
            chunk_numero=chunk_num,
            total_chunks=total_chunks
        )
        max_tokens_para_este_esquema = config.MAX_TOKENS_ESQUEMA_PARCIAL
    else: 
        prompt_final_esquema = prompts.PROMPT_GENERAR_ESQUEMA_TEMPLATE.format(
            texto_completo=texto_para_esquema
        )
        max_tokens_para_este_esquema = config.MAX_TOKENS_ESQUEMA_FUSIONADO
        descripcion_proceso_base = "Esquema Completo (Pase Único)"
    
    logger.info(f"Iniciando Generación de {descripcion_proceso_base}")
    
    # Esta línea estaba duplicada y usaba el template incorrecto para el caso parcial.
    # prompt_final_esquema = prompts.PROMPT_GENERAR_ESQUEMA_TEMPLATE.format(texto_completo=texto_para_esquema)
    # max_tokens_para_este_esquema = config.MAX_TOKENS_ESQUEMA_PARCIAL if es_parcial else config.MAX_TOKENS_ESQUEMA_FUSIONADO
    
    esquema_generado, _, _ = _llamar_al_llm(
        prompt_texto=prompt_final_esquema,
        max_tokens_salida=max_tokens_para_este_esquema,
        temperatura=config.LLM_TEMPERATURE_ESQUEMA,
        descripcion_tarea=descripcion_proceso_base
    )
    return esquema_generado

def fusionar_esquemas(lista_esquemas_parciales):
    if not lista_esquemas_parciales:
        logger.error("No hay esquemas parciales para fusionar.")
        return None
    if len(lista_esquemas_parciales) == 1:
        logger.info("Solo hay un esquema parcial, devolviéndolo directamente (no se necesita fusión).")
        return lista_esquemas_parciales[0]

    logger.info("Iniciando Fusión de Esquemas Parciales")
    
    texto_esquemas_concatenados = ""
    for i, esquema_p in enumerate(lista_esquemas_parciales):
        texto_esquemas_concatenados += f"--- ESQUEMA PARCIAL {i+1} ---\n{esquema_p}\n\n"
    
    prompt_final_fusion = prompts.PROMPT_FUSIONAR_ESQUEMAS_TEMPLATE.format(texto_esquemas_parciales=texto_esquemas_concatenados)

    stop_sequences_fusion = [
        "\n\n--- FIN DE LA RESPUESTA ---",
        "\n---", # Una secuencia más genérica por si acaso
        "\nEste esquema maestro fusionado representa" # Otra parte del texto no deseado
    ]
    
    esquema_fusionado, _, _ = _llamar_al_llm(
        prompt_texto=prompt_final_fusion,
        max_tokens_salida=config.MAX_TOKENS_ESQUEMA_FUSIONADO,
        temperatura=config.LLM_TEMPERATURE_FUSION,
        descripcion_tarea="Fusión de Esquemas",
        stop_sequences=stop_sequences_fusion
    )
    return esquema_fusionado

def generar_apuntes_por_seccion(seccion_esquema_actual, transcripcion_completa, num_seccion=None, total_secciones=None):
    """
    Genera apuntes para una sección específica del esquema, usando la transcripción completa como contexto.
    """
    if llm_instance is None:
        logger.critical("Modelo LLM no cargado. No se pueden generar apuntes para la sección.")
        return "" 
    if not seccion_esquema_actual or not seccion_esquema_actual.strip():
        logger.warning(f"Sección del esquema vacía proporcionada (Sección {num_seccion or '?'}). Saltando.")
        return ""
    if not transcripcion_completa:
        logger.error("Transcripción completa no proporcionada. No se pueden generar apuntes.")
        return ""

    # Extraer un título corto de la sección para logging
    primera_linea_seccion = seccion_esquema_actual.strip().split('\n')[0]
    titulo_seccion_log = re.sub(r"^\s*\d+(\.\d+)*\.\s*", "", primera_linea_seccion).strip() # Quitar numeración
    titulo_seccion_log = titulo_seccion_log[:50] + "..." if len(titulo_seccion_log) > 50 else titulo_seccion_log
    
    descripcion_tarea = f"Apuntes para Sección {num_seccion or '?'}/{total_secciones or '?'} ('{titulo_seccion_log}')"
    logger.info(f"Iniciando generación de {descripcion_tarea}")

    prompt_final_apuntes = prompts.PROMPT_GENERAR_APUNTES_POR_SECCION_TEMPLATE.format(
        seccion_del_esquema_actual=seccion_esquema_actual,
        contexto_relevante_de_transcripcion=transcripcion_completa # Pasando la transcripción completa
    )

    # Advertencia sobre el tamaño del prompt (transcripción completa + sección del esquema + prompt template)
    # Esto es solo una estimación muy burda porque tokenizar todo aquí sería costoso.
    # El conteo real y la advertencia más precisa ocurrirán dentro de _llamar_al_llm.
    len_prompt_aprox_palabras = len(prompt_final_apuntes.split())
    if len_prompt_aprox_palabras * 0.7 > config.CONTEXT_SIZE : # Asumiendo ~0.7 tokens/palabra (muy conservador)
         logger.warning(f"El prompt para '{descripcion_tarea}' (incluyendo transcripción completa) "
                        f"es potencialmente MUY GRANDE (~{len_prompt_aprox_palabras} palabras). "
                        "Podría exceder el límite de contexto.")

    # Definir secuencias de parada para evitar texto no deseado al final de los apuntes de sección
    stop_sequences_apuntes = [
        "\n\n--- FIN DE APUNTES ---", # Ejemplo, ajustar si es necesario
        "\n\n## " # Si empieza a generar la siguiente sección por error
    ]

    apuntes_seccion, _, _ = _llamar_al_llm(
        prompt_texto=prompt_final_apuntes,
        max_tokens_salida=config.MAX_TOKENS_APUNTES_POR_SECCION,
        temperatura=config.LLM_TEMPERATURE_APUNTES,
        descripcion_tarea=descripcion_tarea,
        stop_sequences=stop_sequences_apuntes
    )

    return apuntes_seccion if apuntes_seccion else ""