# Proyecto Final - Generador de Esquemas de Clase con LLM

Este proyecto utiliza un Modelo de Lenguaje Grande (LLM) local para procesar transcripciones de clases universitarias (ej. Optimización o Estructuras de Datos). Si la transcripción es muy larga, se divide en fragmentos (chunks), se genera un esquema parcial para cada uno, y luego estos esquemas parciales se fusionan en un esquema maestro final. El resultado es un esquema jerárquico detallado de la clase en formato de texto.

## Prerrequisitos del Sistema

Antes de empezar, asegúrate de tener instalado lo siguiente en tu sistema:

1.  **Python:** Versión 3.9 o superior.
2.  **Git:** Para clonar el repositorio.
3.  **Herramientas de Compilación C++:** Necesarias para compilar `llama-cpp-python`.
    *   **Windows:** Instala [Build Tools for Visual Studio](https://visualstudio.microsoft.com/es/downloads/) (sección "Herramientas para Visual Studio"). Durante la instalación, selecciona la carga de trabajo **"Desarrollo para el escritorio con C++"**.
    *   **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install build-essential git cmake`
    *   **MacOS:** Instala Xcode Command Line Tools: `xcode-select --install` y `cmake` (ej. `brew install cmake`).
4.  **(Opcional - SOLO para Aceleración por GPU NVIDIA): NVIDIA CUDA Toolkit**
    *   Si tienes una GPU NVIDIA compatible y deseas acelerar el proceso, necesitas instalar el [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads).
    *   **Importante:** Instala una versión compatible con tu driver y GPU. La instalación Express suele ser suficiente y debería añadir `nvcc` a tu PATH.
    *   **Verifica:** Después de instalar (y reiniciar si es necesario), abre una **nueva terminal** y ejecuta `nvcc --version`. Deberías ver la versión impresa. Si no, necesitas añadir la carpeta `bin` de CUDA a tu PATH manualmente.

## Instalación del Proyecto

1.  **Clona el Repositorio:**
    ```bash
    git clone <URL_DE_TU_REPOSITORIO_ACTUALIZADA_SI_ES_NECESARIO>
    cd <NOMBRE_DE_LA_CARPETA_DEL_PROYECTO>
    ```

2.  **Crea y Activa un Entorno Virtual:**
    Es altamente recomendado usar un entorno virtual.
    ```bash
    python -m venv .venv
    ```
    *   Windows (cmd/powershell):
        ```cmd
        .\.venv\Scripts\activate
        ```
    *   Linux/MacOS (bash/zsh):
        ```bash
        source .venv/bin/activate
        ```
    *Verás `(.venv)` al inicio de tu línea de comandos.*

3.  **Instala las Dependencias (si aplica):**
    Si tienes un archivo `requirements.txt` (excluyendo `llama-cpp-python`), instálalo:
    ```bash
    pip install -r requirements.txt
    ```
    *(Si no hay otras dependencias, puedes omitir este paso).*

4.  **Instala `llama-cpp-python` (¡Elige UNA opción!):**

    *   **Opción A: Instalación SOLO para CPU**
        *   Esta es la opción más sencilla si no tienes una GPU NVIDIA o si tienes problemas con la instalación de CUDA.
        ```bash
        pip install llama-cpp-python
        ```

    *   **Opción B: Instalación con Aceleración GPU (NVIDIA CUDA)**
        *   **Asegúrate** de haber completado el Prerrequisito #4 (CUDA Toolkit instalado y `nvcc` funcionando en una nueva terminal).
        *   Ejecuta el comando correspondiente a tu terminal para compilar con soporte CUDA:
            *   **PowerShell (Windows):**
                ```powershell
                $env:CMAKE_ARGS = "-DGGML_CUDA=on"
                pip install --force-reinstall --no-cache-dir llama-cpp-python
                $env:CMAKE_ARGS = ""
                ```
            *   **CMD (Windows):**
                ```cmd
                set CMAKE_ARGS=-DGGML_CUDA=on
                pip install --force-reinstall --no-cache-dir llama-cpp-python
                set CMAKE_ARGS=
                ```
            *   **Bash/Zsh (Linux/MacOS):**
                ```bash
                CMAKE_ARGS="-DGGML_CUDA=on" pip install --force-reinstall --no-cache-dir llama-cpp-python
                ```
                *(Nota: `export` no es necesario si solo se aplica a un comando. `unset` tampoco es estrictamente necesario después si se define así).*
        *   *Presta atención a la salida durante la instalación para verificar que detecta CUDA y compila correctamente.*

## Configuración

1.  **Modelo LLM:**
    *   Descarga un modelo de lenguaje en formato **GGUF**. Se recomienda un modelo instructivo cuantizado (ej. `Mistral-7B-Instruct-v0.2.Q4_K_M.gguf` o `Mistral-7B-Instruct-v0.2.Q2_K.gguf`). Puedes encontrar modelos en [Hugging Face Hub](https://huggingface.co/) (busca los de "TheBloke" o similares).
    *   Crea una carpeta llamada `models/` en la raíz del proyecto (si no existe).
    *   Coloca el archivo `.gguf` descargado dentro de la carpeta `models/`.
    *   Abre el archivo `src/config.py` y actualiza la variable `MODEL_FILENAME` para que coincida **exactamente** con el nombre de tu archivo `.gguf`:
        ```python
        # src/config.py
        MODEL_FILENAME = "nombre_de_tu_modelo.gguf" # ¡CAMBIA ESTO!
        ```

2.  **Transcripción de Entrada:**
    *   Coloca tu archivo de transcripción (en formato `.txt`) dentro de la carpeta `data/` en la raíz del proyecto.
    *   Abre `src/config.py` y asegúrate de que `INPUT_FILE_NAME` apunte al nombre de tu archivo:
        ```python
        # src/config.py
        INPUT_FILE_NAME = "mi_transcripcion.txt" # ¡CAMBIA ESTO SI ES NECESARIO!
        ```
    *   Si el archivo especificado en `INPUT_FILE_PATH` (construido a partir de `INPUT_FILE_NAME`) no existe, el script intentará crear un archivo de ejemplo usando una plantilla ubicada en `templates/ejemplo_transcripcion_template.txt`.

3.  **Otros Parámetros (Opcional):**
    *   Puedes revisar y ajustar otros parámetros en `src/config.py` como `CONTEXT_SIZE`, `MAX_TOKENS_ESQUEMA_PARCIAL`, `MAX_TOKENS_ESQUEMA_FUSIONADO`, `MEGA_CHUNK_CONTEXT_FACTOR`, y `MEGA_CHUNK_OVERLAP_WORDS` (si decides reintroducir el overlap) para optimizar el rendimiento y el uso de memoria según tu hardware y necesidades.

## Ejecución

1.  **Asegúrate de que tu entorno virtual esté activado.**
2.  **Desde la raíz del proyecto** (la carpeta que contiene `src/`, `data/`, etc.), ejecuta el script usando el módulo `src.main`:

    *   **Para usar GPU (comportamiento por defecto, según `config.N_GPU_LAYERS`):**
        ```bash
        python -m src.main
        ```
    *   **Para forzar el uso SÓLO de CPU:**
        ```bash
        python -m src.main --cpu
        ```
        *(Esto requiere que la lógica de `argparse` para el flag `--cpu-only` esté implementada en `src/main.py` y que modifique `config.N_GPU_LAYERS` a `0` antes de cargar el modelo).*

## Salida

*   El esquema jerárquico generado se guardará en la carpeta `output/`. Por defecto, el archivo se llamará `esquema_clase.txt` (configurable mediante `OUTPUT_ESQUEMA_FILENAME` en `src/config.py`).
*   Los logs detallados del proceso se mostrarán en la consola. Si has configurado un `FileHandler` en `src/main.py`, también se guardarán en un archivo de log (ej. `output/schema_generator.log`).

## Solución de Problemas

*   **Error de Compilación de `llama-cpp-python`:** Verifica que todas las **Herramientas de Compilación C++** estén correctamente instaladas y en el PATH. Si usas GPU, asegúrate de que el **CUDA Toolkit** esté instalado, `nvcc` funcione, y estés usando los comandos de instalación correctos para tu sistema operativo que activan la compilación con CUDA.
*   **Error al Cargar el Modelo LLM:**
    *   Verifica que `MODEL_FILENAME` en `src/config.py` sea exacto.
    *   Asegúrate de que el archivo `.gguf` esté en la carpeta `models/`.
    *   Podrías estar quedándote sin RAM/VRAM. Intenta con un modelo más pequeño (menos bits de cuantización o menos parámetros) o reduce `CONTEXT_SIZE` en `src/config.py`.
*   **Resultados Inesperados del Esquema:**
    *   Experimenta con los prompts en `src/prompts.py` (`PROMPT_GENERAR_ESQUEMA_TEMPLATE`, `PROMPT_GENERAR_ESQUEMA_PARCIAL_TEMPLATE`, `PROMPT_FUSIONAR_ESQUEMAS_TEMPLATE`).
    *   Ajusta las temperaturas (`LLM_TEMPERATURE_...`) en `src/config.py`.
    *   Revisa los logs (especialmente en nivel DEBUG) para entender cómo se están dividiendo los chunks y qué se envía al LLM.
    *   Considera el impacto del parámetro `MEGA_CHUNK_OVERLAP_WORDS` (si es mayor que 0) en el número y contenido de los chunks.

