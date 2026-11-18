"""Fronteras entre capas de RetinaSynth.

La interfaz depende de estos protocolos y no de sus implementaciones;
main.py es el único lugar que conoce ambas caras.
"""
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Optional, Protocol

from PIL import Image


# 1. Datos que viajan entre capas

@dataclass(frozen=True)
class PeticionSintesis:
    """Qué generar: cuántas imágenes por grado y con qué truncation."""
    modelo: str
    cantidades: dict[str, int]
    truncation: dict[str, float]
    semilla_inicial: int
    carpeta_salida: Path

    @property
    def total(self) -> int:
        return sum(self.cantidades.values())


@dataclass(frozen=True)
class ResultadoImagen:
    """Una imagen sintética con todo lo necesario para regenerarla."""
    imagen: Image.Image
    modelo: str
    clase: str
    semilla: int
    truncation: float


@dataclass(frozen=True)
class AnalisisDataset:
    """Conteo por grado, faltantes para igualar a la mayoritaria e ignoradas."""
    conteo: dict[str, int]
    faltantes: dict[str, int]
    ignoradas: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Evento:
    """Aviso de progreso emitido por el servicio hacia la interfaz.

    tipo: inicio, estado, imagen, fin, cancelado o error.
    """
    tipo: str
    mensaje: str = ""
    actual: int = 0
    total: int = 0
    ruta: Optional[Path] = None
    imagen: Optional[Image.Image] = field(default=None, repr=False)


# 2. Protocolos que separan las capas

class Generador(Protocol):
    """Produce imágenes de un grado, una por una, con semillas consecutivas."""

    def generar(self, clase: str, cantidad: int, truncation: float,
                semilla_inicial: int) -> Iterator[ResultadoImagen]: ...


class Repositorio(Protocol):
    """Escribe imágenes en disco y lleva el manifiesto."""

    def guardar(self, resultado: ResultadoImagen) -> Path: ...

    def cerrar(self) -> None: ...


class Sintetizador(Protocol):
    """Lo único que la interfaz necesita del núcleo."""

    def analizar_dataset(self, modelo: str,
                         carpeta_dataset: Path) -> AnalisisDataset: ...

    def ejecutar(self, peticion: PeticionSintesis,
                 al_evento: Callable[[Evento], None],
                 cancelar: threading.Event) -> None: ...
