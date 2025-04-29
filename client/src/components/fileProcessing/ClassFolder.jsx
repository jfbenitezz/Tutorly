import { useState, useEffect } from "react";
import "../../routes/fileSystemSimulator/fileSystemSimulator.css";

const processingSteps = [
  "Preprocesando audio",
  "Transcribiendo",
  "Contextualizando con notas",
  "Buscando bibliografía relevante",
  "Generando guía en LaTeX",
  "¡Proceso finalizado! 🎉",
];

const FileIcon = ({ type }) => {
  return <div className={`fs-icon ${type}`} />;
};

const ClassFolder = ({ classData }) => {
  const [processing, setProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1);

  useEffect(() => {
    if (processing && currentStep >= 0 && currentStep < processingSteps.length - 1) {
      const randomDelay = Math.floor(Math.random() * 1200) + 800; // 800ms to 2000ms
      const timeout = setTimeout(() => {
        setCurrentStep((prev) => prev + 1);
      }, randomDelay);
      return () => clearTimeout(timeout);
    }
  }, [processing, currentStep]);

  const handleProcess = () => {
    setProcessing(true);
    setCurrentStep(0);
  };

  return (
    <div className="class-folder">
      <h3>{classData.name}</h3>

      <div className="fs-grid">
        {classData.files.map((file) => (
          <div key={file.id} className="fs-card">
            <FileIcon type={file.type} />
            <p className="fs-name">{file.name}</p>
          </div>
        ))}
      </div>

      {!processing ? (
        <button className="process-btn" onClick={handleProcess}>
          Procesar clase
        </button>
      ) : (
        <div className="progress-box">
          {processingSteps.map((step, index) => (
            <div
              key={index}
              className={`step ${
                index < currentStep
                  ? "done"
                  : index === currentStep
                  ? "current"
                  : ""
              }`}
            >
              {index < currentStep && `✓ ${step}`}
              {index === currentStep && (
                <>
                  {step}... <span className="dot-loader" />
                </>
              )}
              {index > currentStep && step}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ClassFolder;
