from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from typing import List, Optional
import uuid
from pydantic import BaseModel
import shutil
import librosa
import uvicorn

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
AUDIO_UPLOAD_DIR = "audios"
PROCESSED_DIR = "output"
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)