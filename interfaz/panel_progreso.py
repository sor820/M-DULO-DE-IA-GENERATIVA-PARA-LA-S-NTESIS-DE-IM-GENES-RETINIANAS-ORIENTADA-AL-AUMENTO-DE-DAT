"""Seguimiento visual de la generación.

Barra de progreso, contador n de N, bitácora y vista previa de la última
imagen. Todos sus métodos se llaman desde el hilo principal.
"""
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from PIL import Image, ImageTk

from interfaz import estilo

LADO_VISTA = 256
COLORES_BITACORA = {"hora": estilo.CONTORNO, "estado": estilo.PRIMARIO,
                    "fin": estilo.SOBRE_ACENTO, "cancelado": "#b45309",
                    "error": "#dc2626"}


# 1. Panel

class PanelProgreso(ttk.LabelFrame):
    """Muestra el avance; conserva la referencia a la imagen de la vista."""

    def __init__(self, padre: tk.Misc):
        super().__init__(padre, text="Progreso", padding=12)
        visor = tk.Frame(self, bg=estilo.VISOR, padx=10, pady=10)
        visor.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        vacia = Image.new("RGB", (LADO_VISTA, LADO_VISTA), estilo.VISOR)
        self._foto = ImageTk.PhotoImage(vacia, master=self)
        self._vista = tk.Label(visor, image=self._foto, text="Sin imágenes todavía",
                               compound="center", fg=estilo.CONTORNO, bg=estilo.VISOR,
                               bd=0)
        self._vista.pack()
        self._pie = tk.Label(visor, text=" ", fg="#94a3b8", bg=estilo.VISOR,
                             font=(estilo.familia(self), 9))
        self._pie.pack(pady=(6, 0))

        self._barra = ttk.Progressbar(self, mode="determinate")
        self._barra.grid(row=1, column=0, sticky="ew")
        self._contador = ttk.Label(self, text="0 de 0", width=12, anchor="e",
                                   font=(estilo.familia(self), 10, "bold"))
        self._contador.grid(row=1, column=1, sticky="e", padx=(10, 0))

        caja = tk.Frame(self, bg=estilo.BORDE, padx=1, pady=1)
        caja.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        self._bitacora = tk.Text(
            caja, height=10, width=56, state="disabled", wrap="word", bd=0,
            padx=8, pady=6, bg=estilo.SUTIL, fg=estilo.TEXTO_SUAVE,
            font=(estilo.familia_mono(self), 9), highlightthickness=0)
        for etiqueta, color in COLORES_BITACORA.items():
            self._bitacora.tag_configure(etiqueta, foreground=color)
        desplazar = ttk.Scrollbar(caja, command=self._bitacora.yview)
        self._bitacora.configure(yscrollcommand=desplazar.set)
        self._bitacora.pack(side="left", fill="both", expand=True)
        desplazar.pack(side="right", fill="y")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

    # 2. Actualización

    def reiniciar(self, total: int) -> None:
        self._barra.configure(maximum=max(total, 1), value=0)
        self._contador.configure(text=f"0 de {total}")

    def avanzar(self, actual: int, total: int) -> None:
        self._barra.configure(maximum=max(total, 1), value=actual)
        self._contador.configure(text=f"{actual} de {total}")

    def registrar(self, mensaje: str, tipo: str = "") -> None:
        """Agrega una línea; tipo (estado, fin, cancelado, error) le da color."""
        hora = datetime.now().strftime("%H:%M:%S")
        self._bitacora.configure(state="normal")
        self._bitacora.insert("end", f"{hora}  ", "hora")
        self._bitacora.insert("end", f"{mensaje}\n", tipo)
        self._bitacora.see("end")
        self._bitacora.configure(state="disabled")

    def mostrar(self, imagen: Image.Image, nombre: str = "") -> None:
        miniatura = imagen.copy()
        miniatura.thumbnail((LADO_VISTA, LADO_VISTA))
        self._foto = ImageTk.PhotoImage(miniatura, master=self)
        self._vista.configure(image=self._foto, text="")
        self._pie.configure(text=nombre or " ")
