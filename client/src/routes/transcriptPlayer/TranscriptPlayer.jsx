// components/TranscriptPlayer.jsx
import { useEffect, useRef, useState } from "react";
import "./transcriptPlayer.css";

const transcriptMock = [
  { time: 0, text: "...eh... que subieron. Eh eh... usar un sin sin ponerle colores encima, porque como no tienes categoras. Por ejemplo, ponlo de trasplante, si lo quieres mostrar algo para ver si hay diferencia entre los delitos que comenten los hombres y comenten las mujeres. Entonces, sacas el gnero de ah. Modificas con YUMAP y coloreas cada punto por gnero para ver si hay delitos que cometen ms hombres que las mujeres y si hay caractersticas en los datos, cierto delito. Y y para ver si se separa, o sea, para si te queda aqu el grupito de hombres y el grupito de mujeres con las caractersticas que tiene. O sea, ah sera, por ejemplo, por no s. No, lo s simplemente pues, retiras una Pero mira, yo dira que por el tipo de delito que es lo ms. O sea, no s, por ejemplo, narcotrfico. Entonces eh no no. O eh por si cojo delitos eh igual yo aqu puedo coger los yo esto voy a coger los diez que ms se cometen y los otros los voy a dividir en otros. A ver si me entienden lo que lo que yo trato de decir. Lo ms interesante aqu sera ver si t puedes perfilar a los que van a hacer un curso. Cmo haras eso o perfilar a los que van a a a hacer algo. Como ya tienes la informacin, t quitas esa variable de ah y hace clustering en YUMAP usando todas las dems. Y ah se te van a formar grupitos. Despus t colorearas buscando el tipo de delito. Entonces, si t ves que te queda un grupo solo con lo que diga narcotrfico para que te queda otro grupo solo con colores que diga extorsin, es porque s hay diferencias significativas entre las caractersticas de los que son narcotraficantes. Ese es el tipo de preguntas que le vas a hacer a la vida. Ahora tambin puedes hacer una pregunta, eso es de lo que se trata, una pregunta como esa. Ser que el gnero est, el gnero o sexo como le tengas ah ah en tu gnero? Ah, porque en tu mismo. Pero s, ah bueno, porque hay cuatro gneros, tienes razn. Ah s te toca cuatro. Entonces, retiras esas cuatro, verdad? Con el rgimen. Este es el ao del que cometieron el delito. Ao s, ao que cometieron el delito. Esta longitud y latitud, si eso te sirve para el mapa, pero si vas a hacer clustering no es buena idea. Tienes que ver porque se va a terminar simplemente creando un grupo de todos los que cometieron delito en Estados Unidos y Estados Unidos es muy grande, cmo va a esto te puede dar confusin. Al ao y mes. O sea, que cuando vaya a pasar el data set de haga uno, un group by que solamente tenga las columnas con las que voy a trabajar. Ese es el anlisis y probar si esas columnas se determinan algunas otras. En realidad eso es anlisis de correlacin. Se puede a ojo tambin se puede ver. Otra cosa interesante que podramos hacer tiene ms data informacin interesante. Mira, tienes ao y tienes meses. Yo eh bueno, ya sabes que estas no te agregan informacin, pero por ejemplo, cul es el mes del ao donde ms delitos se comenten? Entonces t puedes usar el resto, quitas, quitas ao porque ya no te interesa el ao. Cul es el mes en que ms delitos se cometen? Usar el resto de informacin para ver eh si s, informacin. O simplemente usar el tipo de delito. Y eh y ves para ver cmo se distribuyen los delitos a lo largo del ao. De pronto no hay un no hay, se viaja ms en diciembre porque necesita plata para el intercambio de Navidad. Entonces procura cometer un crimen. Eh, bueno, supongamos que s hay diferencias. Supongamos que s hay diferencias. Pues por ejemplo aqu voy a tener los delitos. Enero, febrero, marzo. Ah, bueno, aqu tendras entonces los meses. La frecuencia de y aqu tendras los delitos ya. S, entonces, cuatro colorcitos por narcotrfico, robo, s s. Se ubican los los puntos. Y yo luego ya decido si los coloreas esos puntos por por ejemplo, por gnero y ah se me iluminar y se ubicaran los, o por tipo de delito. Ah empieza, ah empiezas a sacar informacin de los datos. De eso es de lo que se trata. Esos son los anlisis que t ves en los artculos, lo que ves en en los reportes que se le hacen a las empresas. De eso es de lo que se trata. Bueno, djame, siguiente Bueno, gente, yo yo aqu ya qued claro, ahora me interesa que ustedes busquen su data set en mi computador. Busquen su data. Es Bueno, ya vamos clarito. Entonces, mi es el categrico categrico. S. Tiene? Entonces, tiene que buscar o cuantitativo cuantitativo o cualitativo cuantitativo, si es cuantitativo cuantitativo o cualitativo cuantitativo. No s. El primero en encontrar se queda con ese y el otro le toca el otro. Pero cmo se ve un cuantitativo, o sea, Cuantitativo cuantitativo es el qu, es nmero contra nmeros, cantidades contra cantidades. Cualitativo cuantitativo es qu es eh categoras contra candidatos. Por un valor numrico, un tipo de valor numrico continuo. No discreto, porque si es discreto es cualitativo. Entonces, vamos a empezar ac. Primero aqu. Ahora s yo ya s, esto se usa en anlisis bivariados. Creo que sale del tiempo. Lo que dice busca informacin, o sea y eso es para esto sirve, sirve o no? Bueno, est bien. Ah, eso lo tengo que hacer numrico. Necesito informacin de densidad." }
  
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
