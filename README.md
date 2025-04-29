# 📚 Transcripción Contextual

Este proyecto es una aplicación web diseñada para estudiantes de la asignatura de **Optimización** en la Universidad del Norte. Permite subir grabaciones de clase, notas y bibliografía, para generar automáticamente transcripciones procesadas y guías de estudio exportables en LaTeX o PDF.

---

## 🚀 Funcionalidades principales

### 🗂 Explorador de clases estilo Google Drive
- Visualización por carpetas de clase (Semana 1, Semana 2, etc.).
- Archivos clasificados por tipo: audio, pdf, imagen, video.
- Estilo visual moderno con hover animado y responsive.

### 🔄 Procesamiento simulado por pasos
- Botón **"Procesar clase"** por cada carpeta.
- Animación de pasos: preprocesamiento, transcripción, contextualización y generación de guía.
- Progreso con duraciones aleatorias y loader dinámico.

### 📄 Visualización de guía de estudio
- Versión en LaTeX editable y descargable.
- Generación de PDF estilizado desde un mock.
- Preparado para integración futura con backend real.

---

## 📷 Vista previa
![screenshot](https://github.com/user-attachments/assets/4cda9afd-3f0b-4a14-bdbd-f19533caceca)



> 💡 Asegúrate de tener los íconos `audio.svg`, `pdf.svg`, `video.svg`, `image.svg` en la carpeta `/public/icons/`.

---

## 🛠 Tecnologías utilizadas

- **React + Vite**
- **JavaScript**
- **pdfmake** (para generación de PDF)
- **CSS personalizado**
- **TanStack Query** (para funcionalidad de chat opcional)

---

## ⚙️ Instalación local

1. Clona el repositorio:

```bash
git clone https://github.com/tu-usuario/transcripcion-contextual.git
cd transcripcion-contextual

✍️ Créditos
Desarrollado por: Felipe Benítez, Laura Gómez, Fernando Valencia

Asesores: Prof. Eduardo Zurek, Prof. Daniel Romero

Universidad del Norte, 2025
