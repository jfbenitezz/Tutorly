#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audio Preprocessing Script

This script performs various audio preprocessing steps including:
- Format conversion to WAV
- Resampling
- Volume adjustment
- Noise reduction
- Audio segmentation

Usage:
    audio_preprocessor.py <input_file> [options]

Options:
    --output-dir DIR       Output directory [default: ./output]
    --target-sr RATE       Target sample rate [default: 16000]
    --segment-min MIN      Segment length in minutes [default: 15]
    --overlap-sec SEC      Overlap between segments in seconds [default: 30]
    --gain DB              Volume gain in dB [default: 5]
    --no-noise-reduce      Skip noise reduction step
    --no-segment           Skip segmentation step
"""

import os
from glob import glob
import librosa
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from pydub.silence import split_on_silence
from scipy.signal import medfilt
import wave
import argparse
import traceback


"""# Conversión de formato del audio"""

def convert_to_wav_and_resample(audio_path, output_path="/content/output.wav", target_samplerate=16000, codec="pcm_s16le"):
    """
    Convierte un archivo de audio a formato WAV, mono, 16-bit,
    y lo remuestrea a la tasa de muestreo objetivo usando pydub.

    Args:
        audio_path (str): La ruta al archivo de audio de entrada.
        output_path (str, opcional): La ruta al archivo de salida WAV.
                                         Por defecto, "/content/output.wav".
        target_samplerate (int, opcional): La tasa de muestreo deseada en Hz.
                                             Por defecto, 16000.
        codec (str, opcional): El codec de audio a usar para la conversión.
                               Por defecto, "pcm_s16le" (WAV estándar 16-bit).

    Returns:
        str or None: La ruta al archivo WAV convertido si fue exitoso, None si hubo un error.
    """
    try:
        print(f"Cargando archivo de audio: {audio_path}...")
        # Detecta automáticamente el formato del archivo de entrada
        audio = AudioSegment.from_file(audio_path)
        print(f"Archivo original cargado. Duración: {len(audio)/1000:.2f}s, Canales: {audio.channels}, Tasa: {audio.frame_rate}Hz, Ancho de muestra: {audio.sample_width*8}-bit")

        # 1. Remuestrear a la tasa de muestreo objetivo
        if audio.frame_rate != target_samplerate:
            print(f"Remuestreando de {audio.frame_rate} Hz a {target_samplerate} Hz...")
            audio = audio.set_frame_rate(target_samplerate)
            print(f"Remuestreo completado. Nueva tasa: {audio.frame_rate}Hz")

        # 2. Convertir a mono (1 canal)
        if audio.channels != 1:
            print(f"Convirtiendo de {audio.channels} canales a mono...")
            audio = audio.set_channels(1)
            print("Conversión a mono completada.")

        # Asegurarse de que el directorio de salida existe
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir): # Comprobar si output_dir no es vacío
             os.makedirs(output_dir, exist_ok=True)


        # Exporta al formato WAV con el codec y parámetros especificados
        print(f"Exportando a WAV con codec '{codec}'...")
        audio.export(output_path, format="wav", codec=codec)

        print(f"Archivo convertido y remuestreado exitosamente a WAV: {output_path}")

        # Verificar propiedades del archivo de salida
        with wave.open(output_path, 'rb') as wf_check:
            print(f"Propiedades del archivo de salida '{output_path}':")
            print(f"  Canales: {wf_check.getnchannels()}")
            print(f"  Tasa de muestreo: {wf_check.getframerate()} Hz")
            print(f"  Ancho de muestra: {wf_check.
            getsampwidth()*8}-bit")
            print(f"  Tipo de compresión: {wf_check.getcomptype()}")

        # Audio(output_path) # Descomenta si quieres reproducirlo en Colab
        return output_path

    except Exception as e:
        print(f"Error al convertir el archivo: {e}")
        import traceback
        traceback.print_exc() # Imprimir el traceback completo para más detalles
        return None


def increase_volume_and_save(input_path, output_path, gain_db):
    """
    Aumenta el volumen de un archivo de audio y lo guarda en otro archivo.

    Args:
        audio_path_entrada (str): La ruta al archivo de audio de entrada.
        audio_path_salida (str): La ruta al archivo de audio de salida.
        gain (float): La cantidad de decibelios para aumentar el volumen.
    """
    try:
        # Cargar el audio
        audio = AudioSegment.from_file(input_path)

        # Aumentar el volumen
        audio = audio + gain_db

        # Guardar el audio modificado
        audio.export(output_path, format="wav")
        print(f"Volume increased by {gain_db}dB and saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error al procesar el audio: {e}")
        return None



def reduce_noise(input_path, output_path):
    """
    Aplica reducción de ruido espectral a un archivo de audio.

    Este método realiza una reducción de ruido básica basada en el análisis espectral del audio.
    Asume que el ruido está presente al principio del archivo y crea una máscara para atenuar
    las frecuencias dominadas por el ruido.

    Args:
        file_path (str): La ruta al archivo de audio de entrada.
        output_file_path (str, optional): La ruta al archivo de audio de salida.
                                           Por defecto, "/content/audio_sin_ruido.wav".
    """
    try:
        # 1. Cargar el archivo de audio
        y, sr = librosa.load(input_path, sr=None)

        # 2. Análisis de magnitud y fase
        S_full, phase = librosa.magphase(librosa.stft(y))

        # 3. Estimación del ruido (promedio de los primeros 0.1 segundos)
        noise = np.mean(S_full[:, :int(sr*0.1)], axis=1)

        # 4. Creación de una máscara binaria
        mask = S_full > noise[:, None]

        # 5. Convertir la máscara a tipo float
        mask = mask.astype(float)

        # 6. Aplicar un filtro de mediana para suavizar la máscara
        mask = medfilt(mask, kernel_size=(1,5))

        # 7. Aplicar la máscara a la magnitud
        S_clean = S_full * mask

        # 8. Reconstrucción de la señal de audio
        y_clean = librosa.istft(S_clean * phase)

        # 9. Guardar el archivo de audio limpio
        sf.write(output_path, y_clean, sr)
        print(f"Noise reduced audio saved to: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error durante la reducción de ruido: {e}")
        raise  # Re-lanza la excepción para que se propague
        return None


def split_audio(file_path, output_dir, segment_length_min=15, overlap_sec=30, base_name=None):
    """
    Divide un archivo de audio en segmentos con un traslape especificado y guarda los segmentos en una carpeta.

    Args:
        file_path (str): La ruta al archivo de audio de entrada.
        segment_length_minutes (int, optional): La duración de cada segmento en minutos. Por defecto, 15 minutos.
        overlap_seconds (int, optional): La duración del traslape entre segmentos en segundos. Por defecto, 30 segundos.
        output_dir (str, optional): El nombre de la carpeta donde se guardarán los segmentos. Por defecto, "segment".

    Returns:
        list: Una lista de objetos AudioSegment, donde cada objeto representa un segmento del audio original.
    """

    try:
        audio = AudioSegment.from_file(file_path)
        segment_length_ms = segment_length_min * 60 * 1000
        overlap_ms = overlap_sec * 1000
        step_ms = segment_length_ms - overlap_ms

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        segments = []
        start = 0
        segment_num = 1
        while start < len(audio):
            end = start + segment_length_ms
            segment = audio[start:end]
            output_path = os.path.join(output_dir, f"{base_name}_segment_{segment_num}.wav")
            segment.export(output_path, format="wav")
            segments.append(output_path)
            start += step_ms
            segment_num += 1

        print(f"Audio split into {len(segments)} segments in {output_dir}")
        return segments
    except Exception as e:
        print(f"Error splitting audio: {e}")

"""# Reducción de Ruido

[Remove Background Noise with Fourier Transform in Python
](https://youtu.be/LURaBTYzhj0?si=M6tVsI_KoOTVXPWv)
"""

def process_audio(input_file, output_dir, target_sr=16000, gain_db=5, 
                 segment_min=15, overlap_sec=30, 
                 do_noise_reduction=True, do_segmentation=True):
    """Main processing pipeline for audio files."""
    
    # Create output directory structure
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # Step 1: Convert to WAV and resample
    converted_path = os.path.join(output_dir, f"{base_name}_converted.wav")
    if not convert_to_wav_and_resample(input_file, converted_path, target_sr):
        return False
    
    # Step 2: Increase volume
    volume_path = os.path.join(output_dir, f"{base_name}_volume.wav")
    if not increase_volume_and_save(converted_path, volume_path, gain_db):
        return False
    
    # Step 3: Noise reduction
    if do_noise_reduction:
        clean_path = os.path.join(output_dir, f"{base_name}_clean.wav")
        if not reduce_noise(volume_path, clean_path):
            return False
        processed_path = clean_path
    else:
        processed_path = volume_path
    
    # Step 4: Segmentation
    if do_segmentation:
        segments_dir = os.path.join(output_dir, "segments")
        if not split_audio(processed_path, segments_dir, segment_min, overlap_sec, base_name):
            return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Audio Preprocessing Tool")
    parser.add_argument("input_file", help="Input audio file path")
    parser.add_argument("--output-dir", default="./output", help="Output directory [default: ./output]")
    parser.add_argument("--target-sr", type=int, default=16000, help="Target sample rate [default: 16000]")
    parser.add_argument("--segment-min", type=int, default=15, help="Segment length in minutes [default: 15]")
    parser.add_argument("--overlap-sec", type=int, default=30, help="Overlap between segments in seconds [default: 30]")
    parser.add_argument("--gain", type=int, default=5, help="Volume gain in dB [default: 5]")
    parser.add_argument("--no-noise-reduce", action="store_true", help="Skip noise reduction step")
    parser.add_argument("--no-segment", action="store_true", help="Skip segmentation step")
    
    args = parser.parse_args()
    
    print("\nStarting audio preprocessing...")
    print(f"Input file: {args.input_file}")
    print(f"Output directory: {args.output_dir}")
    print(f"Target sample rate: {args.target_sr} Hz")
    print(f"Volume gain: {args.gain} dB")
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        return
    
    success = process_audio(
        args.input_file,
        args.output_dir,
        target_sr=args.target_sr,
        gain_db=args.gain,
        segment_min=args.segment_min,
        overlap_sec=args.overlap_sec,
        do_noise_reduction=not args.no_noise_reduce,
        do_segmentation=not args.no_segment
    )
    
    if success:
        print("\nAudio preprocessing completed successfully!")
        print(f"Processed files are in: {args.output_dir}")
    else:
        print("\nAudio preprocessing failed")

if __name__ == "__main__":
    main()