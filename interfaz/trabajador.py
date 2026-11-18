"""Ejecución de la síntesis fuera del hilo de la ventana.

El hilo de trabajo solo escribe en una cola; los widgets se tocan
exclusivamente desde el hilo principal, que vacía esa cola.
"""
import queue
import threading
import traceback
from typing import Optional

from nucleo.contratos import Evento, PeticionSintesis, Sintetizador


# 1. Trabajador

class TrabajadorSintesis:
    """Corre el servicio en un threading.Thread y publica eventos en la cola."""

    def __init__(self, servicio: Sintetizador, cola: queue.Queue):
        self._servicio = servicio
        self._cola = cola
        self._cancelar = threading.Event()
        self._hilo: Optional[threading.Thread] = None

    @property
    def ocupado(self) -> bool:
        return self._hilo is not None and self._hilo.is_alive()

    def iniciar(self, peticion: PeticionSintesis) -> None:
        if self.ocupado:
            raise RuntimeError("Ya hay una generación en curso.")
        self._cancelar.clear()
        self._hilo = threading.Thread(target=self._correr, args=(peticion,),
                                      name="sintesis", daemon=True)
        self._hilo.start()

    def cancelar(self) -> None:
        """Pide detenerse; el servicio lo atiende entre imagen e imagen."""
        self._cancelar.set()

    # 2. Cuerpo del hilo

    def _correr(self, peticion: PeticionSintesis) -> None:
        try:
            self._servicio.ejecutar(peticion, self._cola.put, self._cancelar)
        except Exception as error:
            traceback.print_exc()
            self._cola.put(Evento("error", f"{type(error).__name__}: {error}"))
