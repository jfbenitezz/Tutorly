from fastapi import APIRouter, FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import json
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional
import uuid
from pydantic import BaseModel
import shutil
import librosa
import uvicorn
from typing import List, Dict
from vosk import Model, KaldiRecognizer
import wave
from pathlib import Path
from google.generativeai import configure, GenerativeModel
import google.api_core.exceptions

# Import your existing audio processing functions
from preprocessor import (
    process_audio
)

app = FastAPI(
    title="Audio Preprocessing API",
    description="API for audio preprocessing including format conversion, noise reduction, and segmentation",
    version="1.0.0"
)

# Configuration
load_dotenv()  # Load environment variables from .env
AUDIO_UPLOAD_DIR = "audios"
PROCESSED_DIR = "output"
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
VOSK_MODEL_PATH = "vosk-model-small-es-0.42"  # Update with your model path
TRANSCRIPTIONS_DIR = "transcriptions"
os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)
GEMINI_MODEL_NAME = "gemini-1.5-flash" 
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if GEMINI_API_KEY:
    configure(api_key=GEMINI_API_KEY)
    gemini_model = GenerativeModel(GEMINI_MODEL_NAME)

transcribe_router = APIRouter(prefix="/transcribe", tags=["Transcription"])

class AudioProcessingRequest(BaseModel):
    target_sr: int = 16000
    gain_db: int = 5
    segment_min: int = 15
    overlap_sec: int = 30
    do_noise_reduction: bool = True
    do_segmentation: bool = True

class SegmentInfo(BaseModel):
    segment_path: str
    duration_sec: float
    size_bytes: int

class AudioStatusResponse(BaseModel):
    audio_id: str
    original_filename: str
    processing_status: str
    converted_path: Optional[str] = None
    volume_adjusted_path: Optional[str] = None
    noise_reduced_path: Optional[str] = None
    segments: Optional[List[SegmentInfo]] = None
    error: Optional[str] = None

class TranscriptionSegment(BaseModel):
    segment_path: str
    transcription: str
    duration_sec: float

class AudioTranscriptionResponse(BaseModel):
    audio_id: str
    status: str
    segments: List[TranscriptionSegment]
    complete_transcription: str
    transcription_path: str

@app.post("/upload", response_model=AudioStatusResponse)
async def upload_audio(file: UploadFile = File(...)):
    """Upload an audio file for processing"""
    try:
        # Generate unique ID for this audio processing session
        audio_id = str(uuid.uuid4())
        original_filename = file.filename
        file_ext = Path(original_filename).suffix.lower()
        
        # Save the uploaded file
        upload_path = os.path.join(AUDIO_UPLOAD_DIR, f"{audio_id}{file_ext}")
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return AudioStatusResponse(
            audio_id=audio_id,
            original_filename=original_filename,
            processing_status="uploaded",
            converted_path=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/status/{audio_id}", response_model=AudioStatusResponse)
async def get_processing_status(audio_id: str):
    """Check the status of an audio processing job and get output files"""
    try:
        # Check if the audio was uploaded
        uploaded_files = list(Path(AUDIO_UPLOAD_DIR).glob(f"{audio_id}.*"))
        if not uploaded_files:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        original_filename = uploaded_files[0].name
        output_dir = os.path.join(PROCESSED_DIR, audio_id)
        
        if not os.path.exists(output_dir):
            return AudioStatusResponse(
                audio_id=audio_id,
                original_filename=original_filename,
                processing_status="uploaded",
                error="Not processed yet"
            )
        
        # Check what processing steps have been completed
        base_name = os.path.splitext(original_filename)[0]
        response = AudioStatusResponse(
            audio_id=audio_id,
            original_filename=original_filename,
            processing_status="processed"
        )
        
        # Check for each processing step's output
        converted_path = os.path.join(output_dir, f"{base_name}_converted.wav")
        if os.path.exists(converted_path):
            response.converted_path = converted_path
        
        volume_path = os.path.join(output_dir, f"{base_name}_volume.wav")
        if os.path.exists(volume_path):
            response.volume_adjusted_path = volume_path
        
        clean_path = os.path.join(output_dir, f"{base_name}_clean.wav")
        if os.path.exists(clean_path):
            response.noise_reduced_path = clean_path
        
        # Check for segments
        segments_dir = os.path.join(output_dir, "segments")
        if os.path.exists(segments_dir):
            segments = []
            for seg_file in Path(segments_dir).glob("*.wav"):
                duration = librosa.get_duration(filename=str(seg_file))
                segments.append(SegmentInfo(
                    segment_path=str(seg_file),
                    duration_sec=duration,
                    size_bytes=os.path.getsize(seg_file)
                ))
            response.segments = segments
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")
    
@app.post("/process/{audio_id}", response_model=AudioStatusResponse)
async def process_audio_endpoint(
    audio_id: str,
    params: AudioProcessingRequest = AudioProcessingRequest()
):
    """Process an uploaded audio file with the given parameters"""
    try:
        # Find the uploaded file
        uploaded_files = list(Path(AUDIO_UPLOAD_DIR).glob(f"{audio_id}.*"))
        if not uploaded_files:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        input_file = str(uploaded_files[0])
        original_filename = uploaded_files[0].name
        output_dir = os.path.join(PROCESSED_DIR, audio_id)
        # Run the processing pipeline
        success = process_audio(
            input_file=input_file,
            output_dir=output_dir,
            target_sr=params.target_sr,
            gain_db=params.gain_db,
            segment_min=params.segment_min,
            overlap_sec=params.overlap_sec,
            do_noise_reduction=params.do_noise_reduction,
            do_segmentation=params.do_segmentation
        )
        
        if not success:
            return AudioStatusResponse(
                audio_id=audio_id,
                original_filename=original_filename,
                processing_status="failed",
                error="Processing failed - check logs"
            )
        
        # Prepare response with all generated files
        response = AudioStatusResponse(
            audio_id=audio_id,
            original_filename=original_filename,
            processing_status="completed"
        )
        
        # Check for each processing step's output
        base_name = os.path.splitext(original_filename)[0]
        
        # Converted file
        converted_path = os.path.join(output_dir, f"{base_name}_converted.wav")
        if os.path.exists(converted_path):
            response.converted_path = converted_path
        
        # Volume adjusted file
        volume_path = os.path.join(output_dir, f"{base_name}_volume.wav")
        if os.path.exists(volume_path):
            response.volume_adjusted_path = volume_path
        
        # Noise reduced file
        if params.do_noise_reduction:
            clean_path = os.path.join(output_dir, f"{base_name}_clean.wav")
            if os.path.exists(clean_path):
                response.noise_reduced_path = clean_path
        
        # Segments
        if params.do_segmentation:
            segments_dir = os.path.join(output_dir, "segments")
            if os.path.exists(segments_dir):
                segments = []
                for seg_file in Path(segments_dir).glob("*.wav"):
                    # Get duration using librosa
                    duration = librosa.get_duration(filename=str(seg_file))
                    segments.append(SegmentInfo(
                        segment_path=str(seg_file),
                        duration_sec=duration,
                        size_bytes=os.path.getsize(seg_file)
                    ))
                response.segments = segments
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")
    

@app.delete("/cleanup/{audio_id}")
async def cleanup_audio(audio_id: str):
    """Remove all files associated with an audio processing job"""
    try:
        # Delete uploaded file
        uploaded_files = list(Path(AUDIO_UPLOAD_DIR).glob(f"{audio_id}.*"))
        for f in uploaded_files:
            f.unlink()
        
        # Delete processed files
        processed_dir = os.path.join(PROCESSED_DIR, audio_id)
        if os.path.exists(processed_dir):
            shutil.rmtree(processed_dir)
            
        return {"status": "success", "message": f"Removed all files for {audio_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@transcribe_router.post("/{audio_id}", response_model=AudioTranscriptionResponse)
async def transcribe_audio(audio_id: str, use_fallback: bool = False):
    """
    Transcribe all segments for a given audio ID.
    If already transcribed, returns existing transcriptions.
    """
    try:
        # Check if audio exists
        segments_dir = os.path.join(PROCESSED_DIR, audio_id, "segments")
        if not os.path.exists(segments_dir):
            raise HTTPException(status_code=404, detail="Audio segments not found")
        
        # Load Vosk model (do this once at startup in production)
        if not os.path.exists(VOSK_MODEL_PATH):
            raise HTTPException(
                status_code=500,
                detail=f"Vosk model not found at {VOSK_MODEL_PATH}"
            )
        
        model = Model(VOSK_MODEL_PATH)
        
        # Prepare output paths
        transcription_path = os.path.join(TRANSCRIPTIONS_DIR, f"{audio_id}.json")
        
        # Check if already transcribed
        if os.path.exists(transcription_path):
            with open(transcription_path, "r") as f:
                existing_data = json.load(f)
            return AudioTranscriptionResponse(**existing_data)
        
        # Get all segment files
        segment_files = sorted(Path(segments_dir).glob("*.wav"))
        if not segment_files:
            raise HTTPException(
                status_code=404,
                detail="No segment files found"
            )
        
        results = []
        full_transcription = []
        
        for segment_file in segment_files:
            # Transcribe each segment
            segment_path = str(segment_file)
            if not use_fallback:
                transcription = transcribe_segment(model, segment_path)
            else:
                transcription = await transcribe_segment_fallback(segment_path)

            
            # Get duration
            duration = librosa.get_duration(filename=segment_path)
            
            results.append(TranscriptionSegment(
                segment_path=segment_path,
                transcription=transcription,
                duration_sec=duration
            ))
            
            full_transcription.append(transcription)
        
        # Combine all transcriptions
        complete_transcription = " ".join(full_transcription)
        
        # Save results
        response_data = {
            "audio_id": audio_id,
            "status": "completed",
            "segments": [seg.dict() for seg in results],
            "complete_transcription": complete_transcription,
            "transcription_path": transcription_path
        }
        
        with open(transcription_path, "w") as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)
        
        return AudioTranscriptionResponse(**response_data)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )

def transcribe_segment(model: Model, segment_path: str) -> str:
    """Transcribe a single audio segment using Vosk"""
    try:
        with wave.open(segment_path, 'rb') as wf:
            # Verify audio format
            if wf.getnchannels() != 1:
                raise ValueError("Audio must be mono")
            if wf.getsampwidth() != 2:
                raise ValueError("Audio must be 16-bit")
            
            samplerate = wf.getframerate()
            rec = KaldiRecognizer(model, samplerate)
            rec.SetWords(True)
            
            full_text = []
            
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if result.get("text"):
                        full_text.append(result["text"])
            
            # Get final result
            final_result = json.loads(rec.FinalResult())
            if final_result.get("text"):
                full_text.append(final_result["text"])
            
            return " ".join(full_text).strip()
    
    except Exception as e:
        raise ValueError(f"Error transcribing {segment_path}: {str(e)}")

async def transcribe_segment_fallback(audio_path: str) -> str:
    try:
        prompt = "Transcribe este audio en español, se usa lenguaje técnico de una clase universitaria."

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        response = await gemini_model.generate_content_async([
            {"text": prompt},
            {
                "mime_type": "audio/wav",
                "data": audio_bytes
            }
        ])

        if not response.text:
            raise ValueError("Respuesta vacía de Gemini")

        return response.text.strip()

    except google.api_core.exceptions.GoogleAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error de la API de Gemini: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en fallback Gemini: {str(e)}"
        )
    
@transcribe_router.get("/{audio_id}", response_model=AudioTranscriptionResponse)
async def get_transcription_status(audio_id: str):
    """
    Check if a transcription exists for the given audio ID.
    Returns the existing transcription if found, or 404 if not.
    """
    transcription_path = os.path.join(TRANSCRIPTIONS_DIR, f"{audio_id}.json")
    
    if not os.path.exists(transcription_path):
        raise HTTPException(
            status_code=404,
            detail="Transcription not found for this audio ID"
        )
    
    try:
        with open(transcription_path, "r") as f:
            existing_data = json.load(f)
        return AudioTranscriptionResponse(**existing_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading transcription file: {str(e)}"
        )

app.include_router(transcribe_router)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)