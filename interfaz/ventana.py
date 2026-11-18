"""Ventana principal de RetinaSynth.

Arma el layout, traduce el formulario en una PeticionSintesis y vacía
la cola de eventos del trabajador cada 100 ms desde el hilo principal.
"""
import queue
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from config import ConfigModelo
from interfaz import estilo
from interfaz.galeria import Galeria, ruta_en_host
from interfaz.panel_generacion import PanelGeneracion, ParametrosGeneracion
from interfaz.panel_modelo import PanelModelo
from interfaz.panel_progreso import PanelProgreso
from interfaz.trabajador import TrabajadorSintesis
from nucleo.contratos import Evento, PeticionSintesis, Sintetizador

INTERVALO_MS = 100


# 1. Ventana

class VentanaPrincipal:
    """Conecta los paneles con el trabajador; no sabe cómo se sintetiza."""

    def __init__(self, raiz: tk.Tk, servicio: Sintetizador,
                 catalogo: dict[str, ConfigModelo], carpeta_salida: Path,
                 simulado: bool = False):
        self._raiz = raiz
        self._servicio = servicio
        self._cola: queue.Queue = queue.Queue()
        self._trabajador = TrabajadorSintesis(servicio, self._cola)

        estilo.aplicar_estilo(raiz)
        raiz.title("RetinaSynth — síntesis de retinografías")
        raiz.geometry("1080x720")
        raiz.minsize(960, 640)
        raiz.protocol("WM_DELETE_WINDOW", self._cerrar)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(1, weight=1)
        self._encabezado(simulado)

        cuerpo = ttk.Frame(raiz, style="Fondo.TFrame", padding=16)
        cuerpo.grid(row=1, column=0, sticky="nsew")
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)
        izquierda = ttk.Frame(cuerpo, style="Fondo.TFrame")
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self._progreso = PanelProgreso(cuerpo)
        self._progreso.grid(row=0, column=1, sticky="nsew")

        self._generacion = PanelGeneracion(izquierda, carpeta_salida)
        self._modelo = PanelModelo(izquierda, catalogo, self._seleccion_cambiada)
        self._modelo.grid(row=0, column=0, sticky="ew")
        self._generacion.grid(row=1, column=0, sticky="ew", pady=16)

        botones = ttk.Frame(izquierda, style="Fondo.TFrame")
        botones.grid(row=2, column=0, sticky="ew")
        botones.columnconfigure((0, 1), weight=1)
        self._boton_generar = ttk.Button(botones, text="Generar", style="Primario.TButton",
                                         command=self._generar)
        self._boton_generar.grid(row=0, column=0, sticky="ew")
        self._boton_cancelar = ttk.Button(botones, text="Cancelar", state="disabled",
                                          command=self._cancelar)
        self._boton_cancelar.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(botones, text="Abrir galería de la carpeta de salida",
                   command=self._abrir_galeria).grid(row=1, column=0, columnspan=2,
                                                     sticky="ew", pady=(8, 0))

        if simulado:
            self._progreso.registrar("Modo simulado: las imágenes son ruido de prueba.",
                                     "estado")
        self._raiz.after(INTERVALO_MS, self._vaciar_cola)

    def _encabezado(self, simulado: bool) -> None:
        barra = ttk.Frame(self._raiz, style="Encabezado.TFrame", padding=(20, 14))
        barra.grid(row=0, column=0, sticky="ew")
        ttk.Label(barra, text="RetinaSynth", style="Titulo.TLabel").pack(side="left")
        ttk.Label(barra, text="Síntesis de retinografías por grado de severidad",
                  style="Subtitulo.TLabel").pack(side="left", padx=(14, 0), pady=(6, 0))
        if simulado:
            ttk.Label(barra, text="MODO SIMULADO", style="Chip.TLabel").pack(side="right")

    # 2. Acciones del usuario

    def _seleccion_cambiada(self, config: ConfigModelo, grado: str) -> None:
        self._generacion.establecer_truncation(config.truncation_de(grado))

    def _generar(self) -> None:
        try:
            parametros = self._generacion.valores()
            peticion = self._armar_peticion(parametros)
        except (ValueError, OSError) as error:
            messagebox.showerror("RetinaSynth", str(error), parent=self._raiz)
            return
        if peticion is None:
            return
        self._progreso.reiniciar(peticion.total)
        self._ocupado(True)
        self._trabajador.iniciar(peticion)

    def _armar_peticion(self, p: ParametrosGeneracion) -> PeticionSintesis | None:
        config, grado = self._modelo.modelo, self._modelo.grado
        if not p.balanceo:
            return PeticionSintesis(config.codigo, {grado: p.cantidad},
                                    {grado: p.truncation}, p.semilla, p.carpeta_salida)

        analisis = self._servicio.analizar_dataset(config.codigo, p.carpeta_dataset)
        self._progreso.registrar(f"Dataset {p.carpeta_dataset}:")
        for g in config.grados:
            self._progreso.registrar(f"  {g}: {analisis.conteo[g]} reales, "
                                     f"faltan {analisis.faltantes[g]}")
        if analisis.ignoradas:
            self._progreso.registrar("  Carpetas ignoradas: " + ", ".join(analisis.ignoradas))
        total = sum(analisis.faltantes.values())
        if total == 0:
            messagebox.showinfo("RetinaSynth", "El dataset ya está balanceado.",
                                parent=self._raiz)
            return None
        if not messagebox.askyesno(
                "Modo balanceo", f"Se generarán {total} imágenes con la truncation "
                "configurada para cada grado. ¿Continuar?", parent=self._raiz):
            return None
        truncation = {g: config.truncation_de(g) for g in config.grados}
        return PeticionSintesis(config.codigo, analisis.faltantes, truncation,
                                p.semilla, p.carpeta_salida)

    def _cancelar(self) -> None:
        self._trabajador.cancelar()
        self._boton_cancelar.configure(state="disabled")
        self._progreso.registrar("Cancelando al terminar la imagen en curso…", "cancelado")

    def _abrir_galeria(self) -> None:
        Galeria(self._raiz, self._generacion.carpeta_salida)

    def _cerrar(self) -> None:
        if self._trabajador.ocupado:
            if not messagebox.askyesno("RetinaSynth", "Hay una generación en curso. "
                                       "¿Cancelarla y salir?", parent=self._raiz):
                return
            self._trabajador.cancelar()
        self._raiz.destroy()

    # 3. Eventos del trabajador (hilo principal)

    def _vaciar_cola(self) -> None:
        try:
            while True:
                self._atender(self._cola.get_nowait())
        except queue.Empty:
            pass
        self._raiz.after(INTERVALO_MS, self._vaciar_cola)

    def _atender(self, evento: Evento) -> None:
        if evento.tipo == "imagen":
            self._progreso.avanzar(evento.actual, evento.total)
            if evento.imagen is not None:
                nombre = f"{evento.ruta.parent.name} / {evento.ruta.name}" if evento.ruta else ""
                self._progreso.mostrar(evento.imagen, nombre)
            return
        if evento.mensaje:
            self._progreso.registrar(evento.mensaje, evento.tipo)
        if evento.tipo == "inicio":
            self._progreso.reiniciar(evento.total)
        elif evento.tipo in ("fin", "cancelado", "error"):
            self._ocupado(False)
            carpeta = self._generacion.carpeta_salida
            if evento.tipo != "error" and ruta_en_host(carpeta) != str(carpeta.absolute()):
                self._progreso.registrar(f"En Windows: {ruta_en_host(carpeta)}", "fin")
            if evento.tipo == "error":
                messagebox.showerror("RetinaSynth", evento.mensaje, parent=self._raiz)

    def _ocupado(self, ocupado: bool) -> None:
        self._boton_generar.configure(state="disabled" if ocupado else "normal")
        self._boton_cancelar.configure(state="normal" if ocupado else "disabled")
        self._modelo.habilitar(not ocupado)
        self._generacion.habilitar(not ocupado)
