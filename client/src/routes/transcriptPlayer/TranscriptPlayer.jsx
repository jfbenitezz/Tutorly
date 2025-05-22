import { useEffect, useRef, useState } from "react";
import "./transcriptPlayer.css"; // Asegúrate que este archivo CSS existe y está enlazado

const TranscriptPlayer = ({ audioId, processedAudioPath, originalFilenameFromProps, useFallbackForTranscription }) => {
  const audioRef = useRef(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [formattedTranscript, setFormattedTranscript] = useState([]);
  const [audioTitle, setAudioTitle] = useState("Cargando título...");
  const [audioSrc, setAudioSrc] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeLine, setActiveLine] = useState(null);

  useEffect(() => {
    if (audioId) {
      // 1. Establecer el título del audio
      setAudioTitle(originalFilenameFromProps || `Audio ID: ${audioId}`);

      // 2. Construir la URL del audio para el reproductor
      if (processedAudioPath) {
        // processedAudioPath es algo como "output/AUDIO_ID_DEL_PROCESO/nombre_archivo_procesado.wav"
        // o "output\AUDIO_ID_DEL_PROCESO\nombre_archivo_procesado.wav"
        // Necesitamos extraer las partes para el proxy del backend
        const pathParts = processedAudioPath.split(/[/|\\]/); // Manejar tanto / como \
        if (pathParts.length >= 3 && pathParts[0].toLowerCase() === 'output') {
          const fileSpecificAudioId = pathParts[1];
          const relativeFilePath = pathParts.slice(2).join('/');
          setAudioSrc(`/api/audio/file/${fileSpecificAudioId}/${relativeFilePath}`);
        } else {
          console.warn("[TranscriptPlayer] No se pudo parsear 'processedAudioPath' para la URL del audio:", processedAudioPath);
          setError("No se pudo determinar la ruta del archivo de audio para reproducción.");
        }
      } else {
        console.warn("[TranscriptPlayer] No se proporcionó 'processedAudioPath'.");
        setError("No se proporcionó la ruta al archivo de audio procesado.");
      }

      // 3. Cargar la transcripción
      const fetchTranscription = async () => {
        setIsLoading(true);
        setError(null);
        // Asegúrate de que useFallbackForTranscription tenga un valor booleano definido
        // Si no se pasa, puedes asumir un valor por defecto, por ejemplo, false.
        const fallbackValue = typeof useFallbackForTranscription === 'boolean' ? useFallbackForTranscription : false;
        const fetchUrl = `/api/audio/transcribe/${audioId}?use_fallback=${fallbackValue}`;
        
        console.log("[TranscriptPlayer] Fetching transcription from URL:", fetchUrl);

        try {
          const response = await fetch(fetchUrl, {
            method: "POST",
            // No necesitas headers como Content-Type: application/json si el cuerpo está vacío
            // y el backend no lo requiere explícitamente para este endpoint.
          });

          console.log("[TranscriptPlayer] Response OK:", response.ok, "Status:", response.status);

          if (!response.ok) {
            // Intenta parsear el error como JSON, pero ten un fallback si no es JSON
            let errorDetail = `Error HTTP: ${response.status}`;
            try {
              const errorData = await response.json();
              errorDetail = errorData.detail || errorData.error || errorDetail;
            } catch (jsonError) {
              // El cuerpo del error no era JSON, usa el status text o un mensaje genérico
              errorDetail = response.statusText || errorDetail;
              console.warn("[TranscriptPlayer] El cuerpo del error de la respuesta no era JSON.");
            }
            console.error("[TranscriptPlayer] Error data from response:", errorDetail);
            throw new Error(errorDetail);
          }
          const data = await response.json(); //  AudioTranscriptionResponse
          console.log("[TranscriptPlayer] Transcription data received:", data);
          
          if (data.segments && data.segments.length > 0) {
            let cumulativeTime = 0;
            const lines = data.segments.map(segment => {
              const lineData = {
                time: cumulativeTime,
                text: segment.transcription,
                duration: segment.duration_sec // Guardamos la duración por si es útil
              };
              cumulativeTime += segment.duration_sec;
              return lineData;
            });
            setFormattedTranscript(lines);
            console.log("[TranscriptPlayer] Formatted transcript from segments:", lines);
          } else if (data.complete_transcription) {
            // Si no hay segmentos pero sí una transcripción completa, la mostramos como una sola línea
            const completeLine = [{ time: 0, text: data.complete_transcription, duration: audioRef.current?.duration || 0 }];
            setFormattedTranscript(completeLine);
            console.log("[TranscriptPlayer] Formatted transcript from complete_transcription:", completeLine);
          } else {
            setFormattedTranscript([]);
            setError("No se encontraron segmentos de transcripción ni transcripción completa.");
            console.warn("[TranscriptPlayer] No segments or complete_transcription found in data.");
          }

        } catch (err) {
          setError(err.message);
          console.error("[TranscriptPlayer] Fallo al cargar la transcripción:", err);
          setFormattedTranscript([]);
        } finally {
          setIsLoading(false);
        }
      };

      fetchTranscription();
    } else {
      // Resetear si no hay audioId
      setAudioTitle("Sin audio seleccionado");
      setAudioSrc("");
      setFormattedTranscript([]);
      setError(null);
      setIsLoading(false);
    }
  }, [audioId, processedAudioPath, originalFilenameFromProps, useFallbackForTranscription]); // Añade useFallbackForTranscription a las dependencias


  useEffect(() => {
    const audioElement = audioRef.current;
    if (!audioElement) return;

    const updateCurrentTime = () => {
      setCurrentTime(audioElement.currentTime);
    };

    audioElement.addEventListener("timeupdate", updateCurrentTime);
    audioElement.addEventListener("loadedmetadata", updateCurrentTime); // Actualizar al cargar

    return () => {
      audioElement.removeEventListener("timeupdate", updateCurrentTime);
      audioElement.removeEventListener("loadedmetadata", updateCurrentTime);
    };
  }, [audioSrc]); // Re-ejecutar si cambia el src del audio


  useEffect(() => {
    // Encontrar la línea activa basada en currentTime
    // Usamos findLast para el caso de segmentos con duración 0 o muy cortos
    const currentActiveLine = formattedTranscript.findLast(
      (line) => currentTime >= line.time && currentTime < (line.time + line.duration)
    ) || formattedTranscript.findLast( // Fallback por si el último segmento no tiene duración bien definida
      (line) => currentTime >= line.time
    );
    setActiveLine(currentActiveLine);
  }, [currentTime, formattedTranscript]);


  const handleLineClick = (time) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      audioRef.current.play(); // Opcional: iniciar reproducción al hacer clic
    }
  };

  if (!audioId && !isLoading) {
    return <div className="transcript-player-container"><p className="tp-message">No hay audio seleccionado para transcribir.</p></div>;
  }

  return (
    <div className="transcript-player-container">
      <h3 className="tp-audio-title">{audioTitle}</h3> {/* Siempre se muestra si hay audioId o isLoading es true */}
      
      {audioSrc ? (
        <audio ref={audioRef} controls src={audioSrc} className="tp-audio-player" />
      ) : (
        // Solo se muestra si NO está cargando Y no hay audioSrc
        !isLoading && <p className="tp-message error">Ruta del archivo de audio no disponible.</p> 
      )}
      
      {/* Mensaje de carga */}
      {isLoading && <p className="tp-message">Cargando transcripción...</p>}
      
      {/* Mensaje de error */}
      {error && <p className="tp-message error">Error: {error}</p>}

      {/* Muestra las líneas de transcripción */}
      {!isLoading && !error && formattedTranscript.length > 0 && (
        <div className="tp-transcript-lines">
          {formattedTranscript.map((line, i) => (
            <p
              key={i}
              className={`tp-line ${activeLine === line ? "active" : ""}`}
              onClick={() => handleLineClick(line.time)}
            >
              {line.text}
            </p>
          ))}
        </div>
      )}

      {/* Mensaje si no hay transcripción después de cargar y sin errores */}
       {!isLoading && !error && formattedTranscript.length === 0 && audioId && (
         <p className="tp-message">No hay transcripción disponible para este audio.</p>
       )}
    </div>
  );
};

export default TranscriptPlayer;