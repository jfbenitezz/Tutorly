# src/main.py
import time
import os
import re
import logging
import argparse
from src import config
from src import utils
from src import llm_processing
from src import prompts

# --- Configuración del Logging (sin cambios) ---
LOG_LEVEL = logging.INFO
# LOG_LEVEL = logging.DEBUG
log_format = "%(asctime)s [%(levelname)-5s] %(name)-20s %(funcName)-25s L%(lineno)-4d: %(message)s"
logging.basicConfig(
    level=LOG_LEVEL,
    format=log_format,
    handlers=[
        logging.StreamHandler()
        # logging.FileHandler(os.path.join(config.BASE_PROJECT_DIR, "output", "schema_generator.log"), mode='a', encoding='utf-8')
    ]
)
module_logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generador de esquemas y opcionalmente apuntes de clase.")
    parser.add_argument("--cpu", action="store_true", help="Forzar el uso de CPU para el modelo LLM.")
    parser.add_argument("--generar-apuntes", action="store_true", help="Activar la generación de apuntes detallados.")
    args = parser.parse_args()

    script_start_time = time.time()
    module_logger.info("--- INICIO DEL PROCESO ---")
    if args.cpu: module_logger.info("Opción --cpu especificada: Se forzará el uso de CPU.")
    if args.generar_apuntes: module_logger.info("Opción --generar-apuntes especificada.")

    with utils.timed_phase("Inicialización y Carga de Modelo"):
        utils.crear_directorios_necesarios()
        llm_processing.cargar_modelo_llm(use_cpu_only=args.cpu)
        if llm_processing.llm_instance is None:
            module_logger.critical("No se pudo cargar el modelo LLM. Saliendo.")
            return

    texto_completo_transcripcion = ""
    with utils.timed_phase("Preparación de Datos (Lectura de Transcripción)"):
        texto_completo_transcripcion = utils.leer_archivo(config.INPUT_FILE_PATH)
        if not texto_completo_transcripcion:
            module_logger.critical("No se pudo leer el archivo de transcripción. Saliendo.")
            return
        num_palabras_total_leidas = len(texto_completo_transcripcion.split())
        module_logger.info(f"Transcripción leída: {num_palabras_total_leidas} palabras.")

    esquema_final_texto = None

    # --- LÓGICA PARA OBTENER EL ESQUEMA ---
    if args.generar_apuntes:
        module_logger.info("Modo 'generar-apuntes': Intentando cargar esquema existente primero.")
        if os.path.exists(config.OUTPUT_ESQUEMA_PATH):
            esquema_final_texto = utils.leer_archivo(config.OUTPUT_ESQUEMA_PATH)
            if esquema_final_texto:
                module_logger.info(f"Esquema existente cargado exitosamente desde: {config.OUTPUT_ESQUEMA_PATH}")
            else:
                module_logger.warning(f"No se pudo leer el esquema desde {config.OUTPUT_ESQUEMA_PATH}, aunque existe. Se procederá a generar uno nuevo.")
        else:
            module_logger.info(f"No se encontró esquema existente en {config.OUTPUT_ESQUEMA_PATH}. Se procederá a generar uno nuevo.")

    # Si no se generarán apuntes, O si se quieren apuntes pero no se pudo cargar el esquema,
    # entonces generar el esquema.
    if not esquema_final_texto: # Esto cubre el caso de no --generar-apuntes O fallo al cargar para apuntes
        with utils.timed_phase("Generación de Esquema Jerárquico"):
            module_logger.info("Procediendo a generar nuevo esquema.")
            
            num_tokens_prompt_base = 0
            num_tokens_contenido_transcripcion = 0
            # Realizar análisis de tokens solo si vamos a generar esquema
            with utils.timed_phase("Análisis de Tokens para Generación de Esquema"):
                prompt_template_base_texto = prompts.PROMPT_GENERAR_ESQUEMA_TEMPLATE.replace("{texto_completo}", "")
                try:
                    tokens_prompt_base = llm_processing.llm_instance.tokenize(prompt_template_base_texto.encode('utf-8', 'ignore'))
                    num_tokens_prompt_base = len(tokens_prompt_base)
                    module_logger.info(f"Tokens reales del prompt base (para esquema): {num_tokens_prompt_base}")
                except Exception as e:
                    module_logger.critical(f"Error CRÍTICO al tokenizar el prompt base para esquema: {e}. No se puede continuar.", exc_info=True)
                    return

                try:
                    tokens_contenido_transcripcion = llm_processing.llm_instance.tokenize(texto_completo_transcripcion.encode('utf-8', 'ignore'))
                    num_tokens_contenido_transcripcion = len(tokens_contenido_transcripcion)
                    module_logger.info(f"Tokens reales del contenido de la transcripción: {num_tokens_contenido_transcripcion}")
                except Exception as e:
                    module_logger.critical(f"Error CRÍTICO al tokenizar el contenido de la transcripción: {e}. No se puede continuar.", exc_info=True)
                    return
            
            tokens_salida_pase_unico = config.MAX_TOKENS_ESQUEMA_FUSIONADO
            max_tokens_para_contenido_en_pase_unico = int(
                (config.CONTEXT_SIZE * config.MEGA_CHUNK_CONTEXT_FACTOR) - num_tokens_prompt_base - tokens_salida_pase_unico
            )
            max_tokens_para_contenido_en_mega_chunk_individual = int(
                 (config.CONTEXT_SIZE * config.MEGA_CHUNK_CONTEXT_FACTOR) - num_tokens_prompt_base - config.MAX_TOKENS_ESQUEMA_PARCIAL
            )

            if max_tokens_para_contenido_en_pase_unico <=0 or max_tokens_para_contenido_en_mega_chunk_individual <= 0:
                module_logger.critical(f"Cálculo de tokens para contenido de esquema resultó no positivo. "
                                       f"Pase único: {max_tokens_para_contenido_en_pase_unico}, "
                                       f"Chunk: {max_tokens_para_contenido_en_mega_chunk_individual}.")
                return

            if num_tokens_contenido_transcripcion <= max_tokens_para_contenido_en_pase_unico:
                module_logger.info(f"La transcripción ({num_tokens_contenido_transcripcion} tokens) cabe en un solo pase para esquema.")
                esquema_final_texto = llm_processing.generar_esquema_de_texto(texto_completo_transcripcion, es_parcial=False)
            else:
                module_logger.info(f"La transcripción ({num_tokens_contenido_transcripcion} tokens) excede límite para pase único de esquema. "
                                   f"Se usará mega-chunking (límite por chunk: {max_tokens_para_contenido_en_mega_chunk_individual} tokens).")
                if llm_processing.llm_instance is None:
                    module_logger.critical("Instancia LLM no disponible para chunking. Saliendo.")
                    return
                mega_chunks = utils.dividir_en_mega_chunks(
                    texto_completo_transcripcion,
                    max_tokens_para_contenido_en_mega_chunk_individual,
                    config.MEGA_CHUNK_OVERLAP_WORDS,
                    llm_tokenizer_instance=llm_processing.llm_instance
                )
                if not mega_chunks:
                    module_logger.critical("No se pudieron generar mega-chunks. Saliendo.")
                    return

                module_logger.info(f"Transcripción dividida en {len(mega_chunks)} mega-chunks para esquemas parciales.")
                esquemas_parciales = []
                for i, mega_chunk_texto in enumerate(mega_chunks):
                    # ... (lógica de procesar cada mega_chunk y generar esquema_parcial) ...
                    palabras_chunk_actual = len(mega_chunk_texto.split())
                    tokens_chunk_actual_reales = 0 
                    try:
                        if llm_processing.llm_instance: 
                            tokens_chunk_actual_reales = len(llm_processing.llm_instance.tokenize(mega_chunk_texto.encode('utf-8','ignore')))
                    except Exception as e_tok_chunk:
                        module_logger.warning(f"No se pudo tokenizar el mega-chunk {i+1} para logging: {e_tok_chunk}")
                        tokens_chunk_actual_reales = "N/A" 

                    module_logger.info(f"  Procesando mega-chunk {i+1}/{len(mega_chunks)} ({palabras_chunk_actual} palabras, ~{tokens_chunk_actual_reales} tokens).")
                    esquema_parcial = llm_processing.generar_esquema_de_texto(
                        mega_chunk_texto, es_parcial=True, chunk_num=i + 1, total_chunks=len(mega_chunks)
                    )
                    if esquema_parcial:
                        esquemas_parciales.append(esquema_parcial)
                    else:
                        module_logger.warning(f"El esquema parcial para el mega-chunk {i+1} fue vacío o nulo.")
                
                if not esquemas_parciales:
                    module_logger.critical("No se pudieron generar esquemas parciales válidos. Saliendo.")
                    return
                
                module_logger.info(f"Se generaron {len(esquemas_parciales)} esquemas parciales. Fusionando...")
                esquema_final_texto = llm_processing.fusionar_esquemas(esquemas_parciales)
            
            if esquema_final_texto:
                utils.guardar_texto_a_archivo(esquema_final_texto, config.OUTPUT_ESQUEMA_PATH, "esquema de la clase")
            else:
                module_logger.critical("Falló la generación del esquema final.")
                return
    
    # Verificar si tenemos un esquema para proceder (ya sea cargado o generado)
    if not esquema_final_texto or not esquema_final_texto.strip():
        module_logger.critical("No hay esquema disponible para continuar. Saliendo.")
        return

    # --- INICIO: Fase de Generación de Apuntes Detallados (CONDICIONAL) ---
    if args.generar_apuntes:
        if texto_completo_transcripcion: # Asegurarse de que tenemos la transcripción
            with utils.timed_phase("Generación de Apuntes Detallados por Sección"):
                # ... (lógica de generación de apuntes que ya tenías, usando esquema_final_texto) ...
                module_logger.info("Dividiendo el esquema maestro en secciones para generar apuntes.")
                
                secciones_del_esquema = re.split(r"\n(?=\d+\.\s)", esquema_final_texto.strip())
                secciones_del_esquema = [s.strip() for s in secciones_del_esquema if s.strip()]

                apuntes_completos_md = f"# Guía de Estudio Detallada de la Clase\n\n"

                if not secciones_del_esquema:
                    module_logger.warning("No se pudieron identificar secciones principales numeradas en el esquema para apuntes. "
                                          "Intentando generar apuntes para el esquema completo como una sola sección.")
                    if esquema_final_texto.strip(): 
                        apuntes_para_seccion_unica = llm_processing.generar_apuntes_por_seccion(
                            esquema_final_texto,
                            texto_completo_transcripcion,
                            num_seccion=1,
                            total_secciones=1
                        )
                        if apuntes_para_seccion_unica:
                            apuntes_completos_md += f"{apuntes_para_seccion_unica.strip()}\n\n"
                else:
                    module_logger.info(f"Esquema dividido en {len(secciones_del_esquema)} secciones para apuntes.")
                    for i, seccion_esq_texto in enumerate(secciones_del_esquema):
                        module_logger.info(f"  Procesando apuntes para Sección {i+1}/{len(secciones_del_esquema)} del esquema.")
                        
                        apuntes_para_esta_seccion = llm_processing.generar_apuntes_por_seccion(
                            seccion_esq_texto,
                            texto_completo_transcripcion,
                            num_seccion=i+1,
                            total_secciones=len(secciones_del_esquema)
                        )
                        if apuntes_para_esta_seccion:
                            apuntes_completos_md += f"{apuntes_para_esta_seccion.strip()}\n\n"
                        else:
                            titulo_seccion_err = seccion_esq_texto.splitlines()[0] if seccion_esq_texto.splitlines() else f"Sección vacía {i+1}"
                            module_logger.warning(f"No se generaron apuntes para la sección del esquema: '{titulo_seccion_err}'")
                
                if apuntes_completos_md.strip() != "# Guía de Estudio Detallada de la Clase":
                     utils.guardar_texto_a_archivo(apuntes_completos_md.strip(), config.OUTPUT_APUNTES_PATH, "apuntes detallados de la clase")
                else:
                    module_logger.warning("No se generó ningún contenido para los apuntes detallados.")
        else: # Esto no debería ocurrir si el esquema se generó/cargó bien
            module_logger.error("No se puede generar apuntes porque falta la transcripción.")
    else:
        module_logger.info("Generación de apuntes detallados OMITIDA (no se especificó --generar-apuntes).")
    # --- FIN: Fase de Generación de Apuntes Detallados ---

    module_logger.info("--- PROCESO TERMINADO ---")
    script_total_duration = time.time() - script_start_time
    module_logger.info(f"--- Duración Total del Script: {utils.format_duration(script_total_duration)} ---")

if __name__ == "__main__":
    main()