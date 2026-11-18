"""Generadores de imágenes retinianas por grado de severidad.

GeneradorStyleGAN (modelo condicional), GeneradorDireccion (modelo
incondicional con dirección W+) y GeneradorIncondicional (una sola
clase) usan la red real; GeneradorSimulado
cumple el mismo contrato con ruido, para trabajar sin GPU ni .pkl.
"""
import time
from typing import Iterator, Optional

import numpy as np
from PIL import Image

from config import ConfigModelo
from nucleo.contratos import ResultadoImagen
from nucleo.modelo import CargadorModelo, ModeloCargado


# 1. Generador real

class GeneradorStyleGAN:
    """Sintetiza con StyleGAN2-ADA condicional; carga la red al primer uso.

    Cada imagen usa una semilla propia, ruido constante y precisión fp32
    (también en GPU), de modo que la misma semilla y truncation regeneran
    la misma imagen.
    """

    def __init__(self, config: ConfigModelo, cargador: CargadorModelo):
        self._config = config
        self._cargador = cargador
        self._modelo: Optional[ModeloCargado] = None

    def generar(self, clase: str, cantidad: int, truncation: float,
                semilla_inicial: int) -> Iterator[ResultadoImagen]:
        import torch
        modelo = self._obtener_modelo()
        for semilla in range(semilla_inicial, semilla_inicial + cantidad):
            z = np.random.RandomState(semilla).randn(1, modelo.red.z_dim)
            z = torch.from_numpy(z).to(modelo.dispositivo)
            with torch.no_grad():
                img = self._sintetizar(modelo, z, clase, truncation)
            img = (img.permute(0, 2, 3, 1) * 127.5 + 128).clamp(0, 255)
            pixeles = img.to(torch.uint8)[0].cpu().numpy()
            yield ResultadoImagen(Image.fromarray(pixeles, "RGB"),
                                  self._config.codigo, clase, semilla, truncation)

    def _sintetizar(self, modelo: ModeloCargado, z, clase: str, truncation: float):
        """El grado entra como one-hot en la posición que ocupa en config.py."""
        import torch
        etiqueta = torch.zeros([1, modelo.red.c_dim], device=modelo.dispositivo)
        etiqueta[0, self._config.grados.index(clase)] = 1
        return modelo.red(z, etiqueta, truncation_psi=truncation,
                          noise_mode="const", force_fp32=True)

    def _obtener_modelo(self) -> ModeloCargado:
        if self._modelo is None:
            self._modelo = self._cargador.cargar(self._config)
        return self._modelo


class GeneradorDireccion(GeneradorStyleGAN):
    """Sintetiza con un modelo incondicional desplazando w por una dirección.

    w = mapping(z) + alpha · dirección, con el alpha del grado en config.py.
    Es el mismo método de progresión de la tesis, partiendo de una semilla
    en lugar de un paciente.
    """

    def _sintetizar(self, modelo: ModeloCargado, z, clase: str, truncation: float):
        w = modelo.red.mapping(z, None, truncation_psi=truncation)
        w = w + self._config.alphas[clase] * modelo.direccion
        return modelo.red.synthesis(w, noise_mode="const", force_fp32=True)


class GeneradorIncondicional(GeneradorStyleGAN):
    """Sintetiza con un modelo de una sola clase (p. ej. ojos sanos)."""

    def _sintetizar(self, modelo: ModeloCargado, z, clase: str, truncation: float):
        return modelo.red(z, None, truncation_psi=truncation,
                          noise_mode="const", force_fp32=True)


# 2. Generador simulado

class GeneradorSimulado:
    """Devuelve un disco de ruido coloreado con la firma del generador real.

    El tono depende del grado y el ruido de la semilla, así que también
    es reproducible. Sirve para desarrollar y probar la interfaz.
    """

    def __init__(self, config: ConfigModelo, tamano: int = 256,
                 retardo: float = 0.05):
        self._config = config
        self._tamano = tamano
        self._retardo = retardo

    def generar(self, clase: str, cantidad: int, truncation: float,
                semilla_inicial: int) -> Iterator[ResultadoImagen]:
        indice = self._config.grados.index(clase)
        for semilla in range(semilla_inicial, semilla_inicial + cantidad):
            time.sleep(self._retardo)
            imagen = self._imagen(semilla, indice, truncation)
            yield ResultadoImagen(imagen, self._config.codigo, clase,
                                  semilla, truncation)

    def _imagen(self, semilla: int, indice: int, truncation: float) -> Image.Image:
        rng = np.random.RandomState(semilla)
        n = self._tamano
        ruido = rng.rand(16, 16, 3) * truncation
        base = np.array([0.75, 0.30 + 0.08 * indice, 0.10])
        pequena = np.clip(base * 0.6 + ruido * 0.6, 0, 1)
        img = Image.fromarray((pequena * 255).astype(np.uint8), "RGB")
        arreglo = np.asarray(img.resize((n, n), Image.BICUBIC)).copy()
        y, x = np.ogrid[:n, :n]
        fuera = (x - n / 2) ** 2 + (y - n / 2) ** 2 > (n * 0.46) ** 2
        arreglo[fuera] = 0
        return Image.fromarray(arreglo, "RGB")
