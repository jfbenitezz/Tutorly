import { Link } from "react-router-dom";
import "./homepage.css";
import { TypeAnimation } from "react-type-animation";
import { useState } from "react";

const Homepage = () => {
  const [typingStatus, setTypingStatus] = useState("human1");

  return (
    <div className="homepage">
      <img src="/orbital.png" alt="" className="orbital" />
      <div className="left">
        <h1>TUTORLY</h1>
        <h2>Transforma tus clases en herramientas de aprendizaje inteligente</h2>
        <h3>Accede a transcripciones automatizadas, contextualizadas y guías de estudio generadas por IA a partir de tus clases.</h3>
        <Link to="/dashboard">EMPEZEMOS </Link>
      </div>
      <div className="right">
        <div className="imgContainer">
          <div className="bgContainer">
            <div className="bg"></div>
          </div>
          <img src="/bot.png" alt="" className="bot" />
          <div className="chat">
            <img
              src={
                typingStatus === "human1"
                  ? "/human1.jpeg"
                  : typingStatus === "human2"
                  ? "/human2.jpeg"
                  : "bot.png"
              }
              alt=""
            />
            <TypeAnimation
              sequence={[
                "Estudiante: No entiendo el ejemplo de programación lineal",
                2000,
                () => {
                  setTypingStatus("ia");
                },
                "IA: Aquí tienes una guía paso a paso con ejemplos y referencias",
                2000,
                () => {
                  setTypingStatus("estudiante2");
                },
                "Estudiante2: ¿Puedes incluir mis notas en la explicación?",
                2000,
                () => {
                  setTypingStatus("ia");
                },
                "IA: Claro, integré tus notas y la bibliografía para reforzar el tema",
                2000,
                () => {
                  setTypingStatus("estudiante1");
                },
              ]}
              wrapper="span"
              repeat={Infinity}
              cursor={true}
              omitDeletionAnimation={true}
            />

          </div>
        </div>
      </div>
      <div className="terms">
        <img src="/logo.png" alt="" />
        <div className="links">
          <Link to="/">Terms of Service</Link>
          <span>|</span>
          <Link to="/">Privacy Policy</Link>
        </div>
      </div>
    </div>
  );
};

export default Homepage;
