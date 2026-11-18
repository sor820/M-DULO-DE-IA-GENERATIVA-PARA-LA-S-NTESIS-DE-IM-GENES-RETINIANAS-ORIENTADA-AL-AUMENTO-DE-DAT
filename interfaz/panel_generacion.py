"""Parámetros de generación: cantidad, truncation, semilla y carpetas.

En modo balanceo la cantidad la decide el análisis del dataset, por eso
su campo se desactiva y se activa el selector de dataset.
"""
import random
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Optional


# 1. Valores leídos del panel

@dataclass(frozen=True)
class ParametrosGeneracion:
    cantidad: int
    truncation: float
    semilla: int
    carpeta_salida: Path
    balanceo: bool
    carpeta_dataset: Optional[Path]


# 2. Panel

class PanelGeneracion(ttk.LabelFrame):
    """Formulario de generación; valores() valida y devuelve los parámetros."""

    def __init__(self, padre: tk.Misc, carpeta_salida: Path):
        super().__init__(padre, text="Generación", padding=12)
        self._cantidad = tk.StringVar(value="50")
        self._truncation = tk.DoubleVar(value=0.7)
        self._semilla = tk.StringVar(value=str(random.randrange(10**7)))
        self._salida = tk.StringVar(value=str(carpeta_salida))
        self._balanceo = tk.BooleanVar(value=False)
        self._dataset = tk.StringVar()

        self._spin_cantidad = self._fila(0, "Cantidad", ttk.Spinbox(
            self, from_=1, to=100000, textvariable=self._cantidad, width=10))
        self._fila(1, "Truncation ψ", ttk.Spinbox(
            self, from_=0.1, to=1.5, increment=0.05, format="%.2f",
            textvariable=self._truncation, width=10))
        caja = ttk.Frame(self)
        ttk.Entry(caja, textvariable=self._semilla, width=12).pack(side="left")
        ttk.Button(caja, text="Aleatoria", command=self._semilla_aleatoria
                   ).pack(side="left", padx=4)
        self._fila(2, "Semilla inicial", caja)
        self._fila(3, "Carpeta de salida", self._selector(self._salida))

        ttk.Checkbutton(self, text="Modo balanceo (completar un dataset existente)",
                        variable=self._balanceo, command=self._balanceo_cambiado
                        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self._caja_dataset = self._selector(self._dataset)
        self._fila(5, "Dataset", self._caja_dataset)
        self.columnconfigure(1, weight=1)
        self._balanceo_cambiado()

    # 3. Consulta

    @property
    def carpeta_salida(self) -> Path:
        return Path(self._salida.get().strip() or ".")

    def establecer_truncation(self, valor: float) -> None:
        self._truncation.set(round(valor, 2))

    def valores(self) -> ParametrosGeneracion:
        """Lee y valida el formulario; lanza ValueError con un mensaje claro."""
        try:
            cantidad = int(self._cantidad.get())
            truncation = float(self._truncation.get())
            semilla = int(self._semilla.get())
        except (ValueError, tk.TclError):
            raise ValueError("Cantidad, truncation y semilla deben ser números.")
        if cantidad < 1 and not self._balanceo.get():
            raise ValueError("La cantidad debe ser al menos 1.")
        if not 0 < truncation <= 2:
            raise ValueError("Truncation debe estar entre 0 y 2.")
        if not 0 <= semilla < 2**32 - 100000:
            raise ValueError("La semilla debe ser un entero positivo de 32 bits.")
        if not self._salida.get().strip():
            raise ValueError("Elija una carpeta de salida.")
        dataset = self._dataset.get().strip()
        if self._balanceo.get() and not dataset:
            raise ValueError("En modo balanceo hay que elegir la carpeta del dataset.")
        return ParametrosGeneracion(
            cantidad, truncation, semilla, Path(self._salida.get().strip()),
            self._balanceo.get(), Path(dataset) if dataset else None)

    def habilitar(self, activo: bool) -> None:
        for hijo in self._todos(self):
            try:
                hijo.configure(state="normal" if activo else "disabled")
            except tk.TclError:
                pass
        if activo:
            self._balanceo_cambiado()

    # 4. Auxiliares

    def _fila(self, fila: int, texto: str, widget: tk.Widget) -> tk.Widget:
        ttk.Label(self, text=texto).grid(row=fila, column=0, sticky="w", padx=(0, 8))
        widget.grid(row=fila, column=1, sticky="ew", pady=2)
        return widget

    def _selector(self, variable: tk.StringVar) -> ttk.Frame:
        caja = ttk.Frame(self)
        ttk.Entry(caja, textvariable=variable).pack(side="left", fill="x", expand=True)
        ttk.Button(caja, text="…", width=3,
                   command=lambda: self._elegir_carpeta(variable)).pack(side="left", padx=4)
        return caja

    def _elegir_carpeta(self, variable: tk.StringVar) -> None:
        carpeta = filedialog.askdirectory(parent=self, initialdir=variable.get() or None)
        if carpeta:
            variable.set(carpeta)

    def _semilla_aleatoria(self) -> None:
        self._semilla.set(str(random.randrange(10**7)))

    def _balanceo_cambiado(self) -> None:
        activo = self._balanceo.get()
        self._spin_cantidad.configure(state="disabled" if activo else "normal")
        for hijo in self._todos(self._caja_dataset):
            hijo.configure(state="normal" if activo else "disabled")

    @staticmethod
    def _todos(widget: tk.Misc) -> list:
        hijos = []
        for hijo in widget.winfo_children():
            hijos.append(hijo)
            hijos.extend(PanelGeneracion._todos(hijo))
        return hijos
