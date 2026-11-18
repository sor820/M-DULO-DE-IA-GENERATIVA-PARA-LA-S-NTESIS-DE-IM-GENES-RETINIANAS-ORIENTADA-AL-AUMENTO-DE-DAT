"""Selección de modelo y grado de severidad.

El combo de grados se repuebla cada vez que cambia el modelo, a partir
del catálogo de config.py.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from config import ConfigModelo


# 1. Panel

class PanelModelo(ttk.LabelFrame):
    """Dos combos: modelo y grado. Avisa con al_cambiar(config, grado)."""

    def __init__(self, padre: tk.Misc, catalogo: dict[str, ConfigModelo],
                 al_cambiar: Optional[Callable[[ConfigModelo, str], None]] = None):
        super().__init__(padre, text="Modelo", padding=12)
        self._catalogo = catalogo
        self._al_cambiar = al_cambiar
        self._etiquetas = {f"{c.codigo} — {c.nombre}": c.codigo
                           for c in catalogo.values()}

        self._modelo = tk.StringVar()
        self._grado = tk.StringVar()

        ttk.Label(self, text="Enfermedad").grid(row=0, column=0, sticky="w")
        self._combo_modelo = ttk.Combobox(
            self, textvariable=self._modelo, state="readonly", width=42,
            values=list(self._etiquetas))
        self._combo_modelo.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(self, text="Grado").grid(row=1, column=0, sticky="w")
        self._combo_grado = ttk.Combobox(self, textvariable=self._grado,
                                         state="readonly", width=42)
        self._combo_grado.grid(row=1, column=1, sticky="ew", pady=2)
        self.columnconfigure(1, weight=1)

        self._combo_modelo.bind("<<ComboboxSelected>>", self._modelo_cambiado)
        self._combo_grado.bind("<<ComboboxSelected>>", lambda _: self._avisar())
        if self._etiquetas:
            self._combo_modelo.current(0)
            self._modelo_cambiado()

    # 2. Consulta

    @property
    def modelo(self) -> ConfigModelo:
        return self._catalogo[self._etiquetas[self._modelo.get()]]

    @property
    def grado(self) -> str:
        return self._grado.get()

    def habilitar(self, activo: bool) -> None:
        estado = "readonly" if activo else "disabled"
        self._combo_modelo.configure(state=estado)
        self._combo_grado.configure(state=estado)

    # 3. Eventos

    def _modelo_cambiado(self, _=None) -> None:
        grados = list(self.modelo.grados)
        self._combo_grado.configure(values=grados)
        self._combo_grado.current(0)
        self._avisar()

    def _avisar(self) -> None:
        if self._al_cambiar:
            self._al_cambiar(self.modelo, self.grado)
