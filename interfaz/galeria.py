"""Galería de la carpeta de salida.

Miniaturas por grado, con los datos del manifiesto de cada imagen. Como
la aplicación suele correr en un contenedor, también muestra la ruta tal
como se ve en Windows.
"""
import csv
import os
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from config import NOMBRE_MANIFIESTO
from interfaz import estilo

LADO_MINI = 112
ANCHO_CELDA = LADO_MINI + 12
LADO_DETALLE = 256
LIMITE = 200
LOTE = 10


# 1. Ruta en el equipo anfitrión

def ruta_en_host(ruta: Path) -> str:
    """Traduce /salida a C:\\...\\salida leyendo los montajes del contenedor.

    Fuera de un contenedor, o si el montaje no es una unidad de Windows,
    devuelve la ruta sin cambios.
    """
    ruta = Path(ruta).absolute()
    if sys.platform == "win32" or not Path("/proc/self/mountinfo").exists():
        return str(ruta)
    sin_escapes = lambda s: re.sub(r"\\(\d{3})", lambda m: chr(int(m.group(1), 8)), s)
    mejor = None
    for linea in Path("/proc/self/mountinfo").read_text().splitlines():
        campos = linea.split()
        raiz, punto = sin_escapes(campos[3]), sin_escapes(campos[4])
        fuente = sin_escapes(campos[campos.index("-") + 2])
        dentro = ruta == Path(punto) or Path(punto) in ruta.parents
        if dentro and re.fullmatch(r"[A-Za-z]:\\", fuente):
            if mejor is None or len(punto) > len(mejor[1]):
                mejor = (raiz, punto, fuente)
    if mejor is None:
        return str(ruta)
    raiz, punto, unidad = mejor
    partes = [p for p in (raiz.strip("/"), ruta.relative_to(punto).as_posix()) if p not in ("", ".")]
    return unidad + "\\".join(partes).replace("/", "\\")


# 2. Ventana de galería

class Galeria(tk.Toplevel):
    """Explora <carpeta>/<grado>/*.png; las miniaturas cargan por lotes."""

    def __init__(self, padre: tk.Misc, carpeta: Path):
        super().__init__(padre, bg=estilo.FONDO)
        self._carpeta = Path(carpeta)
        self._ruta_host = ruta_en_host(self._carpeta)
        self._manifiesto = self._leer_manifiesto()
        self._fotos: list = []
        self._celdas: list[tk.Label] = []
        self._columnas = 4
        self._foto_detalle = None
        self._tanda = 0
        self.title("RetinaSynth — galería")
        self.geometry("1180x700")
        self.minsize(900, 520)

        self._encabezado()
        cuerpo = ttk.Frame(self, style="Fondo.TFrame", padding=12)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        self._grados = ttk.Treeview(cuerpo, columns=("n",), show="tree headings",
                                    selectmode="browse", height=8)
        self._grados.heading("#0", text="Grado")
        self._grados.heading("n", text="Imágenes")
        self._grados.column("#0", width=150)
        self._grados.column("n", width=80, anchor="e")
        self._grados.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self._grados.bind("<<TreeviewSelect>>", lambda _: self._mostrar_grado())

        marco = ttk.LabelFrame(cuerpo, text="Imágenes", padding=6)
        marco.grid(row=0, column=1, sticky="nsew")
        self._lienzo = tk.Canvas(marco, bg=estilo.TARJETA, highlightthickness=0)
        barra = ttk.Scrollbar(marco, command=self._lienzo.yview)
        self._lienzo.configure(yscrollcommand=barra.set)
        self._lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self._rejilla = tk.Frame(self._lienzo, bg=estilo.TARJETA)
        self._lienzo.create_window((0, 0), window=self._rejilla, anchor="nw")
        self._rejilla.bind("<Configure>", lambda _: self._lienzo.configure(
            scrollregion=self._lienzo.bbox("all")))
        self._lienzo.bind("<Configure>", self._ancho_cambiado)
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind(evento, self._rueda)

        self._detalle(cuerpo)
        self._llenar_grados()

    # 3. Construcción

    def _encabezado(self) -> None:
        barra = ttk.Frame(self, style="Encabezado.TFrame", padding=(16, 12))
        barra.pack(fill="x")
        texto = ttk.Frame(barra, style="Encabezado.TFrame")
        texto.pack(side="left")
        ttk.Label(texto, text="Galería", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(texto, text=self._ruta_host, style="Subtitulo.TLabel").pack(anchor="w")
        ttk.Button(barra, text="Actualizar", command=self._actualizar).pack(side="right")
        ttk.Button(barra, text="Copiar ruta", command=self._copiar_ruta
                   ).pack(side="right", padx=8)
        if sys.platform == "win32":
            ttk.Button(barra, text="Abrir en el Explorador",
                       command=lambda: os.startfile(self._carpeta)).pack(side="right")

    def _detalle(self, padre: ttk.Frame) -> None:
        marco = ttk.LabelFrame(padre, text="Detalle", padding=12)
        marco.grid(row=0, column=2, sticky="ns", padx=(12, 0))
        self._vista = tk.Label(marco, bg=estilo.VISOR, width=LADO_DETALLE // 8,
                               height=LADO_DETALLE // 16, text="Elija una imagen",
                               fg=estilo.CONTORNO)
        self._vista.pack()
        self._datos = ttk.Label(marco, text="", justify="left", width=34,
                                font=(estilo.familia_mono(self), 9))
        self._datos.pack(anchor="w", pady=(10, 0))

    def _llenar_grados(self) -> None:
        self._grados.delete(*self._grados.get_children())
        conteo = {}
        if self._carpeta.is_dir():
            for sub in sorted(p for p in self._carpeta.iterdir() if p.is_dir()):
                conteo[sub.name] = sum(1 for _ in sub.glob("*.png"))
        self._grados.insert("", "end", iid="*", text="Todas", values=(sum(conteo.values()),))
        for nombre, n in conteo.items():
            self._grados.insert("", "end", iid=nombre, text=nombre, values=(n,))
        self._grados.selection_set("*")

    # 4. Miniaturas

    def _mostrar_grado(self) -> None:
        seleccion = self._grados.selection()
        patron = "*/*.png" if not seleccion or seleccion[0] == "*" else f"{seleccion[0]}/*.png"
        archivos = sorted(self._carpeta.glob(patron),
                          key=lambda p: p.stat().st_mtime, reverse=True)
        for hijo in self._rejilla.winfo_children():
            hijo.destroy()
        self._fotos.clear()
        self._celdas.clear()
        self._tanda += 1
        if not archivos:
            ttk.Label(self._rejilla, text="Aún no hay imágenes en esta carpeta.",
                      style="Suave.TLabel").grid(padx=20, pady=20)
            return
        if len(archivos) > LIMITE:
            ttk.Label(self._rejilla, style="Suave.TLabel",
                      text=f"Mostrando las {LIMITE} más recientes de {len(archivos)}"
                      ).grid(row=0, column=0, columnspan=99, sticky="w", padx=6)
        self._cargar_lote(archivos[:LIMITE], 0, self._tanda)

    def _cargar_lote(self, archivos: list[Path], inicio: int, tanda: int) -> None:
        """Carga LOTE miniaturas y cede el turno a la ventana; así no se congela."""
        if tanda != self._tanda:
            return
        for i in range(inicio, min(inicio + LOTE, len(archivos))):
            ruta = archivos[i]
            try:
                imagen = Image.open(ruta)
                imagen.thumbnail((LADO_MINI, LADO_MINI))
            except OSError:
                continue
            foto = ImageTk.PhotoImage(imagen, master=self)
            self._fotos.append(foto)
            celda = tk.Label(self._rejilla, image=foto, bg=estilo.TARJETA, bd=0,
                             highlightthickness=2, highlightbackground=estilo.TARJETA,
                             cursor="hand2")
            self._colocar(celda, len(self._celdas))
            self._celdas.append(celda)
            celda.bind("<Button-1>", lambda _, r=ruta: self._elegir(r))
            celda.bind("<Enter>", lambda _, c=celda: c.configure(highlightbackground=estilo.ACENTO))
            celda.bind("<Leave>", lambda _, c=celda: c.configure(highlightbackground=estilo.TARJETA))
        if inicio + LOTE < len(archivos):
            self.after(1, self._cargar_lote, archivos, inicio + LOTE, tanda)

    def _colocar(self, celda: tk.Label, i: int) -> None:
        celda.grid(row=1 + i // self._columnas, column=i % self._columnas, padx=4, pady=4)

    def _ancho_cambiado(self, evento: tk.Event) -> None:
        """Reacomoda las miniaturas en tantas columnas como quepan."""
        columnas = max(1, evento.width // ANCHO_CELDA)
        if columnas != self._columnas:
            self._columnas = columnas
            for i, celda in enumerate(self._celdas):
                self._colocar(celda, i)

    def _elegir(self, ruta: Path) -> None:
        imagen = Image.open(ruta)
        imagen.thumbnail((LADO_DETALLE, LADO_DETALLE))
        self._foto_detalle = ImageTk.PhotoImage(imagen, master=self)
        self._vista.configure(image=self._foto_detalle, text="", width=0, height=0)
        fila = self._manifiesto.get(ruta.relative_to(self._carpeta).as_posix())
        lineas = [ruta.name, ""]
        if fila:
            lineas += [f"Modelo:      {fila['modelo']}", f"Grado:       {fila['clase']}",
                       f"Semilla:     {fila['semilla']}", f"Truncation:  {fila['truncation']}",
                       f"Fecha:       {fila['fecha'].replace('T', ' ')}"]
        else:
            lineas.append("Sin registro en el manifiesto.")
        self._datos.configure(text="\n".join(lineas))

    # 5. Acciones

    def _leer_manifiesto(self) -> dict[str, dict]:
        ruta = self._carpeta / NOMBRE_MANIFIESTO
        if not ruta.is_file():
            return {}
        with open(ruta, newline="", encoding="utf-8") as f:
            return {fila["archivo"]: fila for fila in csv.DictReader(f)}

    def _actualizar(self) -> None:
        self._manifiesto = self._leer_manifiesto()
        self._llenar_grados()

    def _copiar_ruta(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._ruta_host)

    def _rueda(self, evento: tk.Event) -> None:
        if evento.widget is self._grados:
            return
        paso = -1 if evento.num == 4 or evento.delta > 0 else 1
        self._lienzo.yview_scroll(paso * 2, "units")
