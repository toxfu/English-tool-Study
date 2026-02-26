# Usa PyTorch 2.8 con soporte GPU (CUDA 12.8)
FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime

# Establece el directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema necesarias para algunas librerías Python
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copia los archivos de configuración del proyecto
COPY pyproject.toml .

# Instala uv para gestión de dependencias más rápida
RUN pip install --no-cache-dir uv

# Instala las dependencias del proyecto
RUN uv pip install --system .

# Descarga el modelo de spaCy (ajusta según el modelo que uses)
RUN python -m spacy download en_core_web_sm

# Copia el código fuente
COPY src/ ./src/

# Expone el puerto de Streamlit
EXPOSE 8501

# Agrega src al PYTHONPATH
ENV PYTHONPATH="/app/src" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Comando para ejecutar la aplicación
CMD ["streamlit", "run", "src/gui.py"]