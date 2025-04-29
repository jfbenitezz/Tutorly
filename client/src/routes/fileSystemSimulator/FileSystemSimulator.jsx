import ClassFolder from "../../components/fileProcessing/ClassFolder";
import "./fileSystemSimulator.css";

const classGroups = [
  {
    id: 1,
    name: "Clase Semana 1",
    files: [
      { id: "a", name: "Audio_1.mp3", type: "audio" },
      { id: "b", name: "Notas_1.pdf", type: "pdf" },
    ],
  },
  {
    id: 2,
    name: "Clase Semana 2",
    files: [
      { id: "c", name: "Audio_2.mp3", type: "audio" },
      { id: "d", name: "Bibliografía.pdf", type: "pdf" },
    ],
  },
];

const FileSystemSimulator = () => {
  return (
    <div className="fs-container">
      <h2>Clases Registradas</h2>
      {classGroups.map((group) => (
        <ClassFolder key={group.id} classData={group} />
      ))}
    </div>
  );
};

export default FileSystemSimulator;
