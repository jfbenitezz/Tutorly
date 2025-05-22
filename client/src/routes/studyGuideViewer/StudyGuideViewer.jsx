import { useState, useEffect } from "react";
import pdfMake from "pdfmake/build/pdfmake";
import * as pdfFonts from "pdfmake/build/vfs_fonts";
import "./studyGuideViewer.css"; // Asegúrate de que este archivo CSS esté en la misma carpeta y actualizado
import { FiFileText, FiDownload, FiEdit3, FiZap } from 'react-icons/fi'; // Algunos iconos

pdfMake.vfs = pdfFonts.vfs;

const StudyGuideViewer = ({ completeTranscription, audioTitle = "Clase" }) => {
  const [guideTitle, setGuideTitle] = useState(`Guía de Estudio - ${audioTitle}`);
  const [mainTopics, setMainTopics] = useState(""); // Para los temas principales extraídos o ingresados
  const [detailedNotes, setDetailedNotes] = useState(""); // Para notas detalladas o la transcripción
  const [isEditing, setIsEditing] = useState(false); // Para permitir edición básica

  useEffect(() => {
    // Si recibimos una transcripción, la usamos para las notas detalladas
    if (completeTranscription) {
      setDetailedNotes(completeTranscription);
      // Podrías intentar extraer temas principales aquí si tienes alguna lógica para ello,
      // o dejar que el usuario los ingrese.
      // Por ahora, dejaremos mainTopics vacío para que el usuario lo llene.
    }
    setGuideTitle(`Apuntes de Clase - ${audioTitle}`);
  }, [completeTranscription, audioTitle]);


  const generatePdfContent = () => {
    // Lógica mejorada para generar contenido del PDF
    // Aquí podrías tener una IA o heurísticas para resumir `detailedNotes` en `mainTopics`
    // o simplemente usar lo que el usuario haya ingresado/editado.

    const content = [];

    // Título de la Guía
    content.push({ text: guideTitle, style: "header" });

    // Temas Principales (si existen)
    if (mainTopics.trim() !== "") {
      content.push({ text: "Temas Principales:", style: "subheader" });
      const topicsArray = mainTopics.split('\n').filter(topic => topic.trim() !== "");
      if (topicsArray.length > 0) {
        content.push({ ul: topicsArray, margin: [0, 5, 0, 15] });
      }
    } else {
        content.push({ text: "Transcripción Completa:", style: "subheader" });
    }

    // Notas Detalladas / Transcripción
    if (detailedNotes.trim() !== "") {
        // Podríamos intentar dividir el texto en párrafos para mejor formato en PDF
        const paragraphs = detailedNotes.split(/\n\s*\n/).map(p => p.trim()).filter(p => p !== ""); // Divide por doble salto de línea
        paragraphs.forEach(paragraph => {
            content.push({ text: paragraph, style: "bodyText", margin: [0, 0, 0, 10] });
        });
    }
    
    content.push({ text: "\nFuente: Transcripción automática de la clase.", style: "sourceInfo", italics: true, alignment: 'right' });

    return content;
  };
  
  const generatePdf = () => {
    if (!detailedNotes && !mainTopics) {
        alert("No hay contenido para generar el PDF. Por favor, carga una transcripción o añade notas.");
        return;
    }
    const docDefinition = {
      content: generatePdfContent(),
      styles: {
        header: { fontSize: 20, bold: true, margin: [0, 0, 0, 15], color: '#1a202c' },
        subheader: { fontSize: 16, bold: true, margin: [0, 10, 0, 8], color: '#2d3748' },
        bodyText: { fontSize: 11, lineHeight: 1.4, color: '#4a5568' },
        sourceInfo: { fontSize: 9, color: '#718096' }
      },
      defaultStyle: {
        font: "Roboto" // Asegúrate que las fuentes de pdfMake estén configuradas
      }
    };
    pdfMake.createPdf(docDefinition).open();
  };

  const generateLatexContent = () => {
    // Lógica mejorada para generar contenido LaTeX
    let latexString = `\\documentclass[12pt,a4paper]{article}
\\usepackage[utf8]{inputenc}
\\usepackage{amsmath}
\\usepackage{amsfonts}
\\usepackage{amssymb}
\\usepackage{graphicx}
\\usepackage[left=2cm,right=2cm,top=2cm,bottom=2cm]{geometry}
\\usepackage{parskip} % Para separar párrafos con espacio vertical en vez de indentación

\\title{${guideTitle.replace(/&/g, '\\&').replace(/%/g, '\\%').replace(/#/g, '\\#')}} % Escapar caracteres especiales
\\author{Generado por Tutorly}
\\date{\\today}

\\begin{document}
\\maketitle
\\thispagestyle{empty} % No numerar la página del título
\\clearpage

`;

    if (mainTopics.trim() !== "") {
      latexString += `\\section*{Temas Principales}\n`;
      latexString += `\\begin{itemize}\n`;
      mainTopics.split('\n').filter(topic => topic.trim() !== "").forEach(topic => {
        latexString += `  \\item ${topic.replace(/&/g, '\\&').replace(/%/g, '\\%').replace(/#/g, '\\#')}\n`;
      });
      latexString += `\\end{itemize}\n\n`;
    } else {
        latexString += `\\section*{Transcripción Completa}\n`;
    }

    if (detailedNotes.trim() !== "") {
      // Reemplazar saltos de línea dobles por separación de párrafos en LaTeX
      const paragraphs = detailedNotes.split(/\n\s*\n/).map(p => p.trim()).filter(p => p !== "");
      paragraphs.forEach(paragraph => {
          latexString += `${paragraph.replace(/&/g, '\\&').replace(/%/g, '\\%').replace(/#/g, '\\#')}\n\n`; // Doble salto para nuevo párrafo
      });
    }
    
    latexString += `\n\n\\vfill\n`;
    latexString += `\\hfill \\textit{Fuente: Transcripción automática de la clase.}\n`;
    latexString += `\\end{document}\n`;
    return latexString;
  };

  const downloadLatex = () => {
     if (!detailedNotes && !mainTopics) {
        alert("No hay contenido para generar el archivo LaTeX. Por favor, carga una transcripción o añade notas.");
        return;
    }
    const latexContent = generateLatexContent();
    const blob = new Blob([latexContent], { type: "application/x-tex;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${audioTitle.replace(/\s+/g, '_')}_apuntes.tex`; // Nombre de archivo más dinámico
    link.click();
    URL.revokeObjectURL(link.href); // Limpiar
  };

  return (
    <div className="sg-container">
      <header className="sg-header">
        <FiFileText className="sg-header-icon" />
        <h1>Generador de Apuntes de Clase</h1>
      </header>

      <section className="sg-section sg-input-section">
        <div className="sg-form-group">
          <label htmlFor="guideTitle">Título de los Apuntes:</label>
          <input 
            type="text"
            id="guideTitle"
            className="sg-input"
            value={guideTitle}
            onChange={(e) => setGuideTitle(e.target.value)}
          />
        </div>
        
        {isEditing ? (
            <>
                <div className="sg-form-group">
                    <label htmlFor="mainTopics">Temas Principales (uno por línea):</label>
                    <textarea
                        id="mainTopics"
                        className="sg-textarea"
                        rows="5"
                        value={mainTopics}
                        onChange={(e) => setMainTopics(e.target.value)}
                        placeholder="Ej: Introducción al Método Simplex, Variables de Holgura, Tabla Simplex..."
                    />
                </div>
                <div className="sg-form-group">
                    <label htmlFor="detailedNotes">Notas Detalladas / Transcripción:</label>
                    <textarea
                        id="detailedNotes"
                        className="sg-textarea"
                        rows="15"
                        value={detailedNotes}
                        onChange={(e) => setDetailedNotes(e.target.value)}
                        placeholder="Aquí puedes pegar la transcripción completa o escribir tus notas..."
                    />
                </div>
                 <button onClick={() => setIsEditing(false)} className="sg-button sg-button-secondary">
                    <FiSave className="sg-icon-prefix" /> Finalizar Edición
                </button>
            </>
        ) : (
            <div className="sg-preview-section">
                <h4>Vista Previa del Contenido:</h4>
                <div className="sg-preview-title">{guideTitle}</div>
                {mainTopics && (
                    <>
                        <h5>Temas Principales:</h5>
                        <ul className="sg-preview-list">
                            {mainTopics.split('\n').filter(t => t.trim()).map((topic, i) => <li key={i}>{topic}</li>)}
                        </ul>
                    </>
                )}
                {detailedNotes && (
                    <>
                        <h5>{mainTopics ? "Notas Detalladas:" : "Transcripción:"}</h5>
                        <pre className="sg-preview-notes">{detailedNotes.substring(0, 500)}{detailedNotes.length > 500 ? "..." : ""}</pre>
                    </>
                )}
                 <button onClick={() => setIsEditing(true)} className="sg-button sg-button-edit">
                    <FiEdit3 className="sg-icon-prefix" /> Editar Contenido
                </button>
            </div>
        )}
      </section>

      <section className="sg-section sg-actions-section">
        <h2 className="sg-section-title">Generar y Descargar</h2>
        <div className="sg-button-group">
          <button onClick={generatePdf} className="sg-button sg-button-primary" disabled={!detailedNotes && !mainTopics}>
            <FiZap className="sg-icon-prefix" /> Generar PDF
          </button>
          <button onClick={downloadLatex} className="sg-button sg-button-secondary" disabled={!detailedNotes && !mainTopics}>
            <FiDownload className="sg-icon-prefix" /> Descargar LaTeX (.tex)
          </button>
        </div>
      </section>
    </div>
  );
};

export default StudyGuideViewer;