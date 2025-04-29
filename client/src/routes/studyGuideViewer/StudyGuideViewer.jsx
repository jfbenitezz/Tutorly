import pdfMake from "pdfmake/build/pdfmake";
import * as pdfFonts from "pdfmake/build/vfs_fonts";
import "./studyGuideViewer.css";

pdfMake.vfs = pdfFonts.vfs;

const latexText = `
\\section*{Guía de Estudio - Semana 1}
\\textbf{Tema:} Método Simplex

1. Definición del problema  
2. Restricciones y variables  
3. Ejemplo práctico  

\\textit{Fuente: Apuntes de clase y bibliografía base}
`;

const StudyGuideViewer = () => {
  const generatePdf = () => {
    const docDefinition = {
      content: [
        { text: "Guía de Estudio - Semana 1", style: "header" },
        { text: "Tema: Método Simplex", style: "subheader" },
        {
          ol: [
            "Definición del problema",
            "Restricciones y variables",
            "Ejemplo práctico",
          ],
        },
        { text: "\nFuente: Apuntes de clase y bibliografía base", italics: true },
      ],
      styles: {
        header: { fontSize: 18, bold: true },
        subheader: { fontSize: 14, bold: true, margin: [0, 10, 0, 5] },
      },
    };

    pdfMake.createPdf(docDefinition).open(); // .download("guia.pdf")
  };

  const downloadLatex = () => {
    const blob = new Blob([latexText], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "guia_estudio.tex";
    link.click();
  };

  return (
    <div className="guideViewer">
      <h3>Guía de Estudio</h3>

      <section>
        <h4>Vista en LaTeX:</h4>
        <pre>{latexText}</pre>
        <button onClick={downloadLatex}>Descargar LaTeX (.tex)</button>
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h4>Vista como PDF:</h4>
        <button onClick={generatePdf}>Generar PDF</button>
      </section>
    </div>
  );
};

export default StudyGuideViewer;
