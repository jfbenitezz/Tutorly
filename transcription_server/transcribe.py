#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import queue
import sys
import sounddevice as sd
import wave
import os
import json
# import tempfile # Ya no es necesario para remuestreo de archivo
# import subprocess # Ya no es necesario para ffmpeg
from vosk import Model, KaldiRecognizer, SetLogLevel

# --- Configuración ---
# Asegúrate que esta ruta sea correcta o pásala con --model-path
DEFAULT_MODEL_PATH = r"vosk-model-small-es-0.42"
TARGET_SAMPLERATE = 16000

q = queue.Queue()


def int_or_str(text):
    try:
        return int(text)
    except ValueError:
        return text


def callback_mic(indata, frames, time, status):
    if status:
        sys.stderr.write(str(status) + '\n')
    q.put(bytes(indata))


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-l", "--list-devices", action="store_true",
        help="show list of audio devices and exit")
    args_initial, remaining = parser.parse_known_args()
    if args_initial.list_devices:
        print(sd.query_devices())
        parser.exit(0)

    parser = argparse.ArgumentParser(
        description="Transcribe audio using a Vosk model. Assumes input WAV is 16kHz mono 16-bit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parser])
    parser.add_argument(
        "-i", "--input-file", type=str, metavar="INPUT_WAV_FILE",
        help="Audio file to transcribe (MUST BE WAV format, 16kHz, mono, 16-bit PCM)")
    parser.add_argument(
        "-t", "--transcription-file", type=str, metavar="OUTPUT_TXT_FILE",
        help="File to store the transcription (TXT format)")
    parser.add_argument(
        "-mp", "--model-path", type=str, metavar="MODEL_PATH", default=DEFAULT_MODEL_PATH,
        help=f"Path to the Vosk model directory (default: {DEFAULT_MODEL_PATH})")
    parser.add_argument(
        "-d", "--device", type=int_or_str,
        help="Input device for microphone (numeric ID or substring)")
    parser.add_argument(
        "-r", "--mic-samplerate", type=int, default=TARGET_SAMPLERATE,  # Para el micrófono
        help=f"Sampling rate for microphone (default/target: {TARGET_SAMPLERATE} Hz).")
    parser.add_argument(
        "-raw", "--save-raw-audio", type=str, metavar="RAW_AUDIO_FILE",
        help="Audio file to store raw microphone recording to (RAW int16 format)")

    args = parser.parse_args(remaining)

    # --- Inicializar Modelo ---
    if not os.path.exists(args.model_path):
        print(
            f"Error: Model path '{args.model_path}' not found. Please check the path.", file=sys.stderr)
        parser.exit(1)

    print(f"Loading Vosk model from: {args.model_path}")
    try:
        # SetLogLevel(-1)
        model = Model(args.model_path)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        parser.exit(1)

    # --- Preparar Archivos de Salida ---
    raw_audio_file_writer = None
    transcription_file_writer = None
    if args.save_raw_audio:
        try:
            raw_audio_file_writer = open(args.save_raw_audio, "wb")
            print(f"Raw audio will be saved to: {args.save_raw_audio}")
        except IOError as e:
            print(
                f"Error opening raw audio file {args.save_raw_audio}: {e}", file=sys.stderr)
            raw_audio_file_writer = None
    if args.transcription_file:
        try:
            transcription_file_writer = open(
                args.transcription_file, "w", encoding="utf-8")
            print(f"Transcription will be saved to: {args.transcription_file}")
        except IOError as e:
            print(
                f"Error opening transcription file {args.transcription_file}: {e}", file=sys.stderr)
            transcription_file_writer = None

    try:
        if args.input_file:
            # --- Transcribir desde Archivo WAV (YA DEBE ESTAR EN FORMATO CORRECTO) ---
            if not os.path.exists(args.input_file):
                print(
                    f"Error: Input audio file '{args.input_file}' not found.", file=sys.stderr)
                parser.exit(1)

            print(
                f"Transcribing from file: {args.input_file} (assuming 16kHz, mono, 16-bit WAV)...")
            try:
                with wave.open(args.input_file, 'rb') as wf:
                    if wf.getnchannels() != 1:
                        print(
                            f"Warning: Audio file {args.input_file} is not mono. Results may be poor.", file=sys.stderr)
                    if wf.getsampwidth() != 2:  # 2 bytes = 16 bits
                        print(
                            f"Warning: Audio file {args.input_file} is not 16-bit. Results may be poor.", file=sys.stderr)
                    if wf.getcomptype() != "NONE":
                        print(
                            f"Warning: Audio file {args.input_file} appears to be compressed. Please use PCM WAV. Results may be poor.", file=sys.stderr)

                    file_samplerate = wf.getframerate()
                    if file_samplerate != TARGET_SAMPLERATE:
                        print(
                            f"CRITICAL Warning: Audio file samplerate ({file_samplerate} Hz) IS NOT {TARGET_SAMPLERATE} Hz as expected by the model. Results WILL be poor.", file=sys.stderr)
                        # No se remuestrea aquí, se asume que el usuario lo hizo antes.

                    # Se pasa la tasa del archivo, pero se espera que sea TARGET_SAMPLERATE
                    rec = KaldiRecognizer(model, file_samplerate)
                    rec.SetWords(True)

                    full_transcription_text = ""
                    while True:
                        data = wf.readframes(4000)
                        if len(data) == 0:
                            break
                        if rec.AcceptWaveform(data):
                            result_json = json.loads(rec.Result())
                            if "text" in result_json and result_json["text"]:
                                full_transcription_text += result_json["text"] + " "

                    final_result_json = json.loads(rec.FinalResult())
                    if "text" in final_result_json and final_result_json["text"]:
                        full_transcription_text += final_result_json["text"]

                    full_transcription_text = full_transcription_text.strip()
                    print("\n--- Transcripción Final (Archivo) ---")
                    print(full_transcription_text)

                    if transcription_file_writer:
                        transcription_file_writer.write(
                            full_transcription_text + "\n")
                        print(
                            f"Transcripción guardada en: {args.transcription_file}")

            except wave.Error as e:
                print(
                    f"Error procesando WAV {args.input_file}: {e}. Asegúrate de que sea un WAV válido 16kHz mono 16-bit.", file=sys.stderr)
            except Exception as e:
                print(
                    f"Error inesperado durante la transcripción del archivo: {e}", file=sys.stderr)

        else:
            # --- Transcribir desde Micrófono ---
            print(
                f"Iniciando grabación desde el micrófono (dispositivo: {args.device or 'default'})...")
            # Usar la tasa de muestreo del argumento --mic-samplerate, que por defecto es TARGET_SAMPLERATE
            effective_mic_samplerate = args.mic_samplerate
            if effective_mic_samplerate != TARGET_SAMPLERATE:
                print(
                    f"ADVERTENCIA: La tasa de muestreo del micrófono ({effective_mic_samplerate}Hz) es diferente de la esperada por el modelo ({TARGET_SAMPLERATE}Hz).", file=sys.stderr)
                print(
                    f"             Intentando grabar a {effective_mic_samplerate}Hz, pero para mejores resultados, configura tu micrófono a {TARGET_SAMPLERATE}Hz si es posible.", file=sys.stderr)

            print(
                f"Usando tasa de muestreo para micrófono: {effective_mic_samplerate} Hz.")

            with sd.RawInputStream(samplerate=effective_mic_samplerate, blocksize=8000, device=args.device,
                                   dtype="int16", channels=1, callback=callback_mic):
                print("#" * 80)
                print(
                    f"Escuchando... Presiona Ctrl+C para detener. (Modelo: {os.path.basename(args.model_path)})")
                print("#" * 80)

                # Pasar la tasa real de grabación
                rec = KaldiRecognizer(model, effective_mic_samplerate)
                rec.SetWords(True)
                accumulated_text_mic = []
                while True:
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        result_json_str = rec.Result()
                        result_data = json.loads(result_json_str)
                        if "text" in result_data and result_data["text"]:
                            segment_text = result_data["text"]
                            print(f"Segmento: {segment_text}")
                            accumulated_text_mic.append(segment_text)
                            if transcription_file_writer:
                                transcription_file_writer.write(
                                    segment_text + " ")
                                transcription_file_writer.flush()
                    if raw_audio_file_writer is not None:
                        raw_audio_file_writer.write(data)

    except KeyboardInterrupt:
        print("\nGrabación/Transcripción detenida.")
        # locals() para verificar si la variable existe
        if not args.input_file and 'accumulated_text_mic' in locals() and accumulated_text_mic:
            final_mic_text = " ".join(accumulated_text_mic).strip()
            print("\n--- Transcripción Final (Micrófono) ---")
            print(final_mic_text)
            if transcription_file_writer and not transcription_file_writer.closed:
                transcription_file_writer.write("\n")
        parser.exit(0)
    except Exception as e:
        sys.stderr.write(type(e).__name__ + ": " + str(e) + '\n')
        traceback.print_exc(file=sys.stderr)
        parser.exit(1)
    finally:
        print("Cerrando archivos...")
        if raw_audio_file_writer and not raw_audio_file_writer.closed:
            raw_audio_file_writer.close()
        if transcription_file_writer and not transcription_file_writer.closed:
            transcription_file_writer.close()

        # Ya no hay archivo temporal de audio para eliminar
        # if temp_audio_file_to_process and os.path.exists(temp_audio_file_to_process):
        #     ...
        print("Finalizado.")


if __name__ == "__main__":
    import traceback
    main()
