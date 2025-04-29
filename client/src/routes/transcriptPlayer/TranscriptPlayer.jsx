// components/TranscriptPlayer.jsx
import { useEffect, useRef, useState } from "react";
import "./transcriptPlayer.css";

const transcriptMock = [
  { time: 0, text: "Bienvenidos a la clase de Optimización..." },
  { time: 5, text: "Hoy hablaremos del método simplex..." },
  { time: 10, text: "Primero definimos las restricciones..." },
  { time: 15, text: "Restricciones son las limitaciones para el problema..." },
  { time: 20, text: "Por ejemplo, en este caso, la restricción es que el costo sea menor a 1000..." },
  { time: 25, text: "Luego definimos las variables..." },
  { time: 30, text: "Variables son las incógnitas del problema..." },
  { time: 35, text: "En este caso, las variables son la cantidad de cada ingrediente..." },
  { time: 40, text: "Luego definimos la función objetivo..." },
  { time: 45, text: "La función objetivo es la que queremos maximizar o minimizar..." },
  { time: 50, text: "En este caso, la función objetivo es el costo total..." },
  { time: 55, text: "Finalmente, aplicamos el método simplex..." },
  { time: 60, text: "El método simplex es un algoritmo para encontrar el valor óptimo..." },
  { time: 65, text: "El resultado es el valor óptimo de cada variable..." },
  { time: 70, text: "En este caso, el resultado es que la cantidad óptima de cada ingrediente es..." },
  { time: 75, text: "En resumen, el método simplex es un algoritmo para encontrar el valor óptimo..." },
];

const TranscriptPlayer = () => {
  const audioRef = useRef(null);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      if (audioRef.current) {
        setCurrentTime(audioRef.current.currentTime);
      }
    }, 500);

    return () => clearInterval(interval);
  }, []);

  const getActiveLine = () =>
    transcriptMock.findLast((line) => currentTime >= line.time);

  return (
    <div className="transcriptPlayer">
      <audio ref={audioRef} controls src="/mock-audio.mp3" />
      <div className="transcript">
        {transcriptMock.map((line, i) => (
          <p
            key={i}
            className={
              currentTime >= line.time ? "active" : ""
            }
          >
            {line.text}
          </p>
        ))}
      </div>
    </div>
  );
};

export default TranscriptPlayer;
