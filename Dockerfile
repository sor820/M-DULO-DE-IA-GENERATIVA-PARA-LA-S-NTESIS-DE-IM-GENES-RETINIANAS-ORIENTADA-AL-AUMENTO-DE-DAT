# ==========================================================
# IMAGEN BASE
# ==========================================================
#
# La variante -devel, no -runtime: trae nvcc, que es lo que
# StyleGAN2-ADA necesita para compilar al vuelo sus kernels
# (upfirdn2d, bias_act). Con -runtime esa compilación falla
# y cae a la implementación lenta de referencia.
#
# ==========================================================

FROM nvidia/cuda:12.8.0-devel-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ==========================================================
# DEPENDENCIAS DEL SISTEMA
# ==========================================================
#
# python3-tk no se instala con pip: Tkinter es un paquete del
# sistema operativo. Sin esta línea, "import tkinter" falla
# dentro del contenedor.
#
# build-essential y ninja-build son para la compilación de
# los kernels de CUDA.
#
# ==========================================================

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-tk \
    build-essential \
    ninja-build \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ==========================================================
# PYTORCH
# ==========================================================
#
# Misma versión que RetinaScan, que ya está probada contra
# estos modelos.
#
# Si `torch.cuda.get_device_capability()` devuelve (12, 0)
# —GPU de la serie 50, arquitectura Blackwell— estas versiones
# NO funcionan. En ese caso, al construir:
#
#   docker compose build \
#     --build-arg TORCH=2.7.0+cu128 \
#     --build-arg TORCHVISION=0.22.0+cu128 \
#     --build-arg INDEX=https://download.pytorch.org/whl/cu128
#
# ==========================================================

ARG TORCH=2.5.1+cu121
ARG TORCHVISION=0.20.1+cu121
ARG INDEX=https://download.pytorch.org/whl/cu121

RUN pip install --no-cache-dir \
    torch==${TORCH} \
    torchvision==${TORCHVISION} \
    --index-url ${INDEX}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
