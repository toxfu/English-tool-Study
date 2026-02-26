# English Study App

Aplicación de estudio de inglés con Streamlit, usando FSRS para repetición espaciada y LLMs para asistencia.

La asistencia con IA ayuda a generar ejemplos con las palabras y frases que hayas agregado, según un tema que elijas. El fin de esta generación es evitar la memorización mecánica y fomentar el aprendizaje contextual. También cuenta con un chat libre para practicar conversaciones en inglés.

https://github.com/user-attachments/assets/55ce4485-665f-4563-83b8-be85b38d707e

## 🚀 Inicio Rápido con Docker

### Prerrequisitos
- Docker
- Docker Compose
- Se necesita soporte para GPU, asegúrate de tener nvidia-docker instalado.

### Ejecución

```bash
# Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down

# Reconstruir después de cambios en dependencias
docker-compose up -d --build
```

La aplicación estará disponible en: http://localhost:8501


## Desarrollo Local sin Docker

```bash
# crear y activar entorno virtual con conda
conda create -n english-study python=3.12 -y
conda activate english-study

# O usando uv (más rápido)
conda install uv
uv pip install -e .

# Descargar modelo de spaCy
python -m spacy download en_core_web_sm

# Ejecutar aplicación
streamlit run src/gui.py
```
