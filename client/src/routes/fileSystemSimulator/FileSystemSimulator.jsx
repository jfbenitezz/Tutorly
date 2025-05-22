import { useState, useRef, useEffect } from "react";
import axios from "axios";
// Importando iconos de React Icons
import { FiUpload, FiSave, FiRefreshCw, FiAlertTriangle } from 'react-icons/fi';
import { FaFileAudio, FaFileAlt, FaCheckCircle, FaTimesCircle } from 'react-icons/fa';
import { AiOutlineLoading3Quarters } from 'react-icons/ai';
import { MdCancel, MdCloudUpload } from 'react-icons/md';
import "./fileSystemSimulator.css";

const BACKEND_PROXY_URL = "http://localhost:3000";

// --- Funciones API ---
const uploadAudio = async (file) => {
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await axios.post(`${BACKEND_PROXY_URL}/api/audio/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data", },
      withCredentials: true,
    });
    return response.data;
  } catch (error) {
    console.error("Error al subir el audio:", error.response ? error.response.data : error.message);
    throw error;
  }
};

const getAudioStatus = async (audioId) => {
  try {
    const response = await axios.get(`${BACKEND_PROXY_URL}/api/audio/status/${audioId}`, {
      withCredentials: true,
    });
    return response.data;
  } catch (error) {
    console.error("Error al obtener el estado del audio:", error.response ? error.response.data : error.message);
    throw error;
  }
};

const processAudio = async (audioId, options = {}) => {
  try {
    const response = await axios.post(`${BACKEND_PROXY_URL}/api/audio/process/${audioId}`, options, {
      withCredentials: true,
    });
    return response.data;
  } catch (error) {
    console.error("Error al procesar el audio:", error.response ? error.response.data : error.message);
    throw error;
  }
};

const transcribeAudio = async (audioId, options = {}) => {
  // options podría ser, por ejemplo, { use_fallback: true } o { use_fallback: false }
  let url = `${BACKEND_PROXY_URL}/api/audio/transcribe/${audioId}`;
  const queryParams = new URLSearchParams();
  if (options.use_fallback !== undefined) {
    queryParams.append('use_fallback', options.use_fallback);
  }
  const queryString = queryParams.toString();
  if (queryString) {
    url += `?${queryString}`;
  }
  try {
    const response = await axios.post(url, {}, { withCredentials: true, });
    return response.data;
  } catch (error) {
    console.error("Error al transcribir el audio (frontend):", error.response ? error.response.data : error.message);
    throw error;
  }
};

const cleanupAudio = async (audioId) => {
  try {
    const response = await axios.delete(`${BACKEND_PROXY_URL}/api/audio/cleanup/${audioId}`, {
      withCredentials: true,
    });
    return response.data;
  } catch (error) {
    console.error("Error al limpiar el audio:", error.response ? error.response.data : error.message);
    throw error;
  }
};
// --- FIN Funciones API ---


function FileSystemSimulator() {
  const audioInputRef = useRef(null);
  const pdfInputRef = useRef(null);

  const [audioFile, setAudioFile] = useState(null);
  const [pdfFile, setPdfFile] = useState(null);
  const [audioId, setAudioId] = useState(null);

  const [currentProcessStatus, setCurrentProcessStatus] = useState(null);
  const [transcriptionData, setTranscriptionData] = useState(null);
  const [overallProgress, setOverallProgress] = useState('idle');

  const [isLoading, setIsLoading] = useState(false);
  const [currentError, setCurrentError] = useState(null);
  const [pollingIntervalId, setPollingIntervalId] = useState(null);
  const [outputFileName, setOutputFileName] = useState("transcripcion.txt");

  const [useFallback, setUseFallback] = useState(false); // <--- NUEVO ESTADO para el fallback

  const simulatedSaveLocation = "la ubicación de guardado predeterminada";

  useEffect(() => {
    return () => {
      if (pollingIntervalId) {
        clearInterval(pollingIntervalId);
      }
    };
  }, [pollingIntervalId]);

  const addFileToSimulatedFS = (fileName, content) => {
    console.log(`Guardando transcripción "${fileName}" con contenido...`);
    alert(`Transcripción "${fileName}" guardada (simulado) en ${simulatedSaveLocation}.`);
  };

  const handleAudioFileSelect = (file) => {
    if (isLoading) return;
    setAudioFile(file);
    setAudioId(null);
    setCurrentProcessStatus(null);
    setTranscriptionData(null);
    setCurrentError(null);
    setOverallProgress('idle');
    if (file) {
      const baseName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
      setOutputFileName(`${baseName}_transcripcion.txt`);
    }
  };

  const handlePdfFileSelect = (file) => {
    if (isLoading) return;
    setPdfFile(file);
    alert(`Archivo PDF seleccionado: ${file.name}. La integración de PDF está pendiente.`);
  };

  const resetState = (statusMessage = 'idle') => {
    setIsLoading(false);
    setAudioFile(null);
    setPdfFile(null);
    setAudioId(null);
    setCurrentProcessStatus(null);
    setTranscriptionData(null);
    setOverallProgress(statusMessage);
    if (audioInputRef.current) audioInputRef.current.value = "";
    if (pdfInputRef.current) pdfInputRef.current.value = "";
    if (pollingIntervalId) {
      clearInterval(pollingIntervalId);
      setPollingIntervalId(null);
    }
  };

  const startAudioProcessingFlow = async () => {
    if (!audioFile) return;
    setIsLoading(true);
    setCurrentError(null);
    setOverallProgress('uploading');
    let currentAudioId = null;
    try {
      const uploadResult = await uploadAudio(audioFile);
      if (!uploadResult || !uploadResult.audio_id) throw new Error("Fallo en la subida: no se recibió audio_id.");
      currentAudioId = uploadResult.audio_id;
      setAudioId(currentAudioId);
      setCurrentProcessStatus(uploadResult.processing_status);
      setOverallProgress('processing_audio');
      const processParams = { target_sr: 16000, gain_db: 5, segment_min: 15, overlap_sec: 30, do_noise_reduction: true, do_segmentation: true };
      const processResult = await processAudio(currentAudioId, processParams);
      setCurrentProcessStatus(processResult.processing_status);

      if (processResult.processing_status === "completed" || processResult.processing_status === "processed") {
        setOverallProgress('transcribing');
        // USAREMOS EL ESTADO useFallback AQUÍ
        const transResult = await transcribeAudio(currentAudioId, { use_fallback: useFallback });
        setTranscriptionData(transResult);
        setOverallProgress('completed');
        setIsLoading(false);
      } else if (processResult.processing_status === "failed") {
        throw new Error(processResult.error || "Fallo durante el procesamiento del audio en el servidor.");
      } else {
        const interval = setInterval(async () => {
          if (!currentAudioId) {
            clearInterval(interval);
            setPollingIntervalId(null);
            return;
          }
          try {
            const statusResult = await getAudioStatus(currentAudioId);
            setCurrentProcessStatus(statusResult.processing_status);
            if (statusResult.processing_status === "completed" || statusResult.processing_status === "processed") {
              clearInterval(interval); setPollingIntervalId(null); setOverallProgress('transcribing');
              // USAREMOS EL ESTADO useFallback AQUÍ TAMBIÉN
              const transResult = await transcribeAudio(currentAudioId, { use_fallback: useFallback });
              setTranscriptionData(transResult); setOverallProgress('completed'); setIsLoading(false);
            } else if (statusResult.processing_status === "failed") {
              clearInterval(interval); setPollingIntervalId(null);
              throw new Error(statusResult.error || "El procesamiento del audio falló en el servidor.");
            }
          } catch (pollError) {
            clearInterval(interval); setPollingIntervalId(null);
            if (!(pollError.response && pollError.response.status === 404 && (overallProgress === 'cancelled' || overallProgress === 'cleaning'))) {
              throw pollError;
            } else {
              console.warn("Polling detenido, audio no encontrado (posiblemente después de cleanup/cancel).");
            }
          }
        }, 5000);
        setPollingIntervalId(interval);
      }
    } catch (error) {
      console.error("Error en el flujo de transcripción:", error);
      setCurrentError(error.message || "Ocurrió un error desconocido.");
      setOverallProgress('failed'); setIsLoading(false);
    }
  };

  const handleCancelAndCleanup = async () => {
    const currentAudioIdToClean = audioId;
    if (pollingIntervalId) { clearInterval(pollingIntervalId); setPollingIntervalId(null); }

    resetState('cancelled');
    setCurrentError(null);

    if (currentAudioIdToClean) {
      setIsLoading(true);
      setOverallProgress('cleaning');
      try {
        await cleanupAudio(currentAudioIdToClean);
        console.log(`Limpieza solicitada para audio ID: ${currentAudioIdToClean}`);
        setOverallProgress('cancelled');
      } catch (error) {
        console.error("Error al limpiar el audio en el servidor:", error);
        setCurrentError("Error al limpiar los archivos del servidor.");
        setOverallProgress('failed_cleanup');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleSave = () => {
    if (!transcriptionData || !transcriptionData.complete_transcription) return;
    addFileToSimulatedFS(outputFileName, transcriptionData.complete_transcription);
  };

  const getStatusInfo = (status) => {
    switch (status) {
      case 'uploading': return { text: "Subiendo audio...", icon: AiOutlineLoading3Quarters, className: "status-progress status-uploading" };
      case 'processing_audio': return { text: `Procesando... (Etapa: ${currentProcessStatus || 'iniciando'})`, icon: AiOutlineLoading3Quarters, className: "status-progress status-processing" };
      case 'transcribing': return { text: "Transcribiendo...", icon: AiOutlineLoading3Quarters, className: "status-progress status-transcribing" };
      case 'completed': return { text: "Completado.", icon: FaCheckCircle, className: "status-success status-completed" };
      case 'failed': return { text: "Fallido.", icon: FaTimesCircle, className: "status-error status-failed" };
      case 'cancelled': return { text: "Cancelado.", icon: MdCancel, className: "status-neutral status-cancelled" };
      case 'cleaning': return { text: "Limpiando...", icon: AiOutlineLoading3Quarters, className: "status-progress status-cleaning" };
      case 'failed_cleanup': return { text: "Fallo limpieza.", icon: FiAlertTriangle, className: "status-error status-failed-cleanup" };
      default: return { text: "Selecciona un archivo de audio.", icon: null, className: "status-idle" };
    }
  };

  const currentStatusInfo = getStatusInfo(overallProgress);
  const IconComponent = currentStatusInfo.icon;

  return (
    <div className="fss-container">
      <header className="fss-header">
        <div className="fss-header-main-title">Sistema de Transcripción de Audio</div>
        <p className="fss-header-subtitle">Sube, procesa y transcribe tus archivos de audio fácilmente.</p>
      </header>

      <main className="fss-content-wrapper">
        <section className="fss-section">
          <h2 className="fss-section-title">1. Cargar Archivos</h2>
          <div className="fss-upload-grid">
            {/* Carga de Audio */}
            <div className="fss-upload-area-wrapper">
              <input
                ref={audioInputRef}
                type="file"
                accept="audio/*"
                onChange={(e) => e.target.files && e.target.files.length > 0 && handleAudioFileSelect(e.target.files[0])}
                className="fss-file-input"
                id="audio-upload-input"
                disabled={isLoading || overallProgress === 'completed'}
              />
              <label
                htmlFor="audio-upload-input"
                className={`fss-upload-area ${isLoading || overallProgress === 'completed' ? "disabled" : ""} ${audioFile ? "has-file" : "type-audio"}`}
              >
                {audioFile ? (
                  <>
                    <FaCheckCircle className="fss-upload-icon-status success" />
                    <p className="fss-upload-filename">{audioFile.name}</p>
                    <p className="fss-upload-filesize">{Math.round(audioFile.size / 1024)} KB</p>
                  </>
                ) : (
                  <>
                    <MdCloudUpload className="fss-upload-icon-main type-audio" />
                    <p className="fss-upload-prompt">Arrastra o selecciona audio</p>
                    <p className="fss-upload-hint">MP3, WAV, M4A, etc.</p>
                  </>
                )}
              </label>
            </div>
            {/* Carga de PDF */}
            <div className="fss-upload-area-wrapper">
              <input
                ref={pdfInputRef}
                type="file"
                accept=".pdf,.txt,.doc,.docx"
                onChange={(e) => e.target.files && e.target.files.length > 0 && handlePdfFileSelect(e.target.files[0])}
                className="fss-file-input"
                id="pdf-upload-input"
                disabled={isLoading}
              />
              <label
                htmlFor="pdf-upload-input"
                className={`fss-upload-area ${isLoading ? "disabled" : ""} ${pdfFile ? "has-file" : "type-document"}`}
              >
                {pdfFile ? (
                  <>
                    <FaCheckCircle className="fss-upload-icon-status success" />
                    <p className="fss-upload-filename">{pdfFile.name}</p>
                    <p className="fss-upload-filesize">{Math.round(pdfFile.size / 1024)} KB</p>
                  </>
                ) : (
                  <>
                    <FaFileAlt className="fss-upload-icon-main type-document" />
                    <p className="fss-upload-prompt">Subir documento (Opcional)</p>
                    <p className="fss-upload-hint">PDF, TXT, DOC</p>
                  </>
                )}
              </label>
            </div>
          </div>
        </section>

        <div className="fss-actions-and-status-container">
          <section className="fss-section fss-actions-section">
            <h2 className="fss-section-title">2. Iniciar Proceso</h2>

            {/* Opción de Fallback */}
            <div className="fss-fallback-option"> {/* Usaremos este contenedor */}
              <input
                type="checkbox"
                id="use-fallback-checkbox"
                checked={useFallback}
                onChange={(e) => setUseFallback(e.target.checked)}
                disabled={isLoading || !audioFile || (overallProgress && !['idle', 'failed', 'cancelled', 'failed_cleanup'].includes(overallProgress))}
                className="fss-fallback-checkbox-input" // Nueva clase para el input
              />
              <label htmlFor="use-fallback-checkbox" className="fss-fallback-checkbox-label"> {/* Nueva clase para el label */}
                {/* El texto del label puede o no estar visible dependiendo del diseño final del switch */}
                <span className="fss-fallback-switch-ui"></span> {/* Elemento para el UI del switch */}
                Usar IA Avanzada (más lento/costoso) {/* Texto descriptivo */}
              </label>
            </div>

            <div className="fss-actions-buttons-wrapper">
              <button
                onClick={startAudioProcessingFlow}
                disabled={!audioFile || isLoading || (overallProgress && !['idle', 'failed', 'cancelled', 'failed_cleanup'].includes(overallProgress))}
                className="fss-button fss-button-primary"
              >
                {isLoading && ['uploading', 'processing_audio', 'transcribing'].includes(overallProgress) ? (
                  <AiOutlineLoading3Quarters className="fss-icon-prefix loading-animate" />
                ) : (
                  <FiUpload className="fss-icon-prefix" />
                )}
                {isLoading && ['uploading', 'processing_audio', 'transcribing'].includes(overallProgress) ? 'Procesando...' : 'Iniciar Transcripción'}
              </button>
              <button
                onClick={handleCancelAndCleanup}
                disabled={(!audioFile && !audioId) || (isLoading && overallProgress === 'cleaning')}
                className="fss-button fss-button-secondary"
              >
                {isLoading && overallProgress === 'cleaning' ? (
                  <AiOutlineLoading3Quarters className="fss-icon-prefix loading-animate" />
                ) : (
                  <MdCancel className="fss-icon-prefix" />
                )}
                {isLoading && overallProgress === 'cleaning' ? 'Limpiando...' : 'Cancelar y Limpiar'}
              </button>
            </div>
          </section>

          {(overallProgress && overallProgress !== 'idle' || currentError) && (
            <section className="fss-section fss-status-results-section">
              <h2 className="fss-section-title fss-status-title-inline">3. Estado</h2>

              <div className={`fss-status-banner ${currentStatusInfo.className}`}>
                {IconComponent && <IconComponent className={`fss-icon-prefix ${isLoading && !['completed', 'failed', 'cancelled', 'failed_cleanup', 'idle'].includes(overallProgress) ? 'loading-animate' : ''}`} />}
                <span>{currentStatusInfo.text}</span>
              </div>

              {currentError && (
                <div className="fss-error-box">
                  <FiAlertTriangle className="fss-icon-prefix" />
                  <div>
                    <p className="fss-error-title">Error:</p>
                    <p>{currentError}</p>
                  </div>
                </div>
              )}
            </section>
          )}
        </div>

        {overallProgress === 'completed' && transcriptionData && transcriptionData.complete_transcription && (
          <section className="fss-section fss-completed-results-section">
            <h2 className="fss-section-title">Resultados de la Transcripción</h2>
            <div className="fss-results-container">
              <h3 className="fss-results-subtitle">Transcripción Completa:</h3>
              <div className="fss-transcription-output">
                <pre>{transcriptionData.complete_transcription}</pre>
              </div>

              <div className="fss-save-form-container">
                <h3 className="fss-save-form-title">
                  <FiSave className="fss-icon-prefix" />
                  Guardar Transcripción
                </h3>
                <div className="fss-form-row">
                  <div className="fss-form-group full-width">
                    <label htmlFor="transcription-filename-save">Nombre del Archivo</label>
                    <input
                      type="text"
                      id="transcription-filename-save"
                      value={outputFileName}
                      onChange={(e) => setOutputFileName(e.target.value)}
                      className="fss-form-input"
                      placeholder="transcripcion.txt"
                    />
                  </div>
                  <button
                    onClick={handleSave}
                    className="fss-button fss-button-success"
                  >
                    <FiSave className="fss-icon-prefix" />
                    Guardar
                  </button>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default FileSystemSimulator;