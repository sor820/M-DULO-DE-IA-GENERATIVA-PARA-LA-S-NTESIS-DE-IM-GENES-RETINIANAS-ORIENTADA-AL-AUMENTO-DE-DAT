"""Orquestación de una sesión de síntesis.

Une generador, repositorio y analizador, y avisa del progreso con
eventos. Es lo único del núcleo que la interfaz llama.
"""
import threading
from pathlib import Path
from typing import Callable

from config import ConfigModelo
from nucleo.balanceo import AnalizadorDataset
from nucleo.contratos import (AnalisisDataset, Evento, Generador,
                              PeticionSintesis, Repositorio)

FabricaGenerador = Callable[[ConfigModelo], Generador]
FabricaRepositorio = Callable[[Path], Repositorio]


# 1. Servicio

class ServicioSintesis:
    """Ejecuta peticiones de síntesis y conserva los generadores ya cargados."""

    def __init__(self, catalogo: dict[str, ConfigModelo],
                 fabrica_generador: FabricaGenerador,
                 fabrica_repositorio: FabricaRepositorio,
                 analizador: AnalizadorDataset):
        self._catalogo = catalogo
        self._fabrica_generador = fabrica_generador
        self._fabrica_repositorio = fabrica_repositorio
        self._analizador = analizador
        self._generadores: dict[str, Generador] = {}

    def analizar_dataset(self, modelo: str, carpeta_dataset: Path) -> AnalisisDataset:
        return self._analizador.analizar(carpeta_dataset,
                                         self._catalogo[modelo].grados)

    def ejecutar(self, peticion: PeticionSintesis,
                 al_evento: Callable[[Evento], None],
                 cancelar: threading.Event) -> None:
        """Genera todas las imágenes pedidas; se detiene limpio al cancelar."""
        self._validar(peticion)
        total = peticion.total
        al_evento(Evento("inicio", f"Generando {total} imágenes", 0, total))
        al_evento(Evento("estado", f"Preparando modelo {peticion.modelo}…"))
        generador = self._generador(peticion.modelo)

        hechas, semilla = 0, peticion.semilla_inicial
        repositorio = self._fabrica_repositorio(peticion.carpeta_salida)
        try:
            for clase, cantidad in peticion.cantidades.items():
                if cantidad <= 0:
                    continue
                psi = peticion.truncation[clase]
                al_evento(Evento("estado", f"{clase}: {cantidad} imágenes, ψ={psi}"))
                for resultado in generador.generar(clase, cantidad, psi, semilla):
                    if cancelar.is_set():
                        al_evento(Evento("cancelado", "Cancelado por el usuario",
                                         hechas, total))
                        return
                    ruta = repositorio.guardar(resultado)
                    hechas += 1
                    al_evento(Evento("imagen", ruta.name, hechas, total,
                                     ruta, resultado.imagen))
                semilla += cantidad
        finally:
            repositorio.cerrar()
        al_evento(Evento("fin", f"Listo: {hechas} imágenes en "
                                f"{peticion.carpeta_salida}", hechas, total))

    # 2. Auxiliares

    def _generador(self, codigo: str) -> Generador:
        if codigo not in self._generadores:
            self._generadores[codigo] = self._fabrica_generador(self._catalogo[codigo])
        return self._generadores[codigo]

    def _validar(self, peticion: PeticionSintesis) -> None:
        config = self._catalogo.get(peticion.modelo)
        if config is None:
            raise ValueError(f"Modelo desconocido: {peticion.modelo}")
        desconocidas = set(peticion.cantidades) - set(config.grados)
        if desconocidas:
            raise ValueError(f"Grados no válidos: {', '.join(sorted(desconocidas))}")
        if peticion.total <= 0:
            raise ValueError("No hay imágenes que generar.")
