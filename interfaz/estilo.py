"""Identidad visual de RetinaSynth.

Paleta tomada de RetinaScan (azul clínico y verde menta) para que ambas
obras se reconozcan como de la misma familia. Todo color vive aquí.
"""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


# 1. Paleta

PRIMARIO = "#0759a8"
PRIMARIO_OSCURO = "#05467f"
PRIMARIO_APAGADO = "#9bb7d4"
ACENTO = "#52e6b0"
SOBRE_ACENTO = "#075985"
FONDO = "#f8fafc"
TARJETA = "#ffffff"
SUTIL = "#f1f5f9"
BORDE = "#e2e8f0"
TEXTO = "#0f172a"
TEXTO_SUAVE = "#334155"
CONTORNO = "#64748b"
VISOR = "#0f172a"


# 2. Tipografía

def familia(raiz: tk.Misc) -> str:
    disponibles = set(tkfont.families(raiz))
    for candidata in ("Segoe UI", "Inter", "DejaVu Sans"):
        if candidata in disponibles:
            return candidata
    return "TkDefaultFont"


def familia_mono(raiz: tk.Misc) -> str:
    disponibles = set(tkfont.families(raiz))
    for candidata in ("Cascadia Mono", "Consolas", "DejaVu Sans Mono"):
        if candidata in disponibles:
            return candidata
    return "TkFixedFont"


# 3. Tema ttk

def aplicar_estilo(raiz: tk.Tk) -> None:
    """Configura el tema clam con la paleta; se llama una vez al arrancar."""
    letra = familia(raiz)
    for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
        tkfont.nametofont(nombre).configure(family=letra, size=10)
    raiz.configure(bg=FONDO)
    raiz.option_add("*TCombobox*Listbox.background", TARJETA)
    raiz.option_add("*TCombobox*Listbox.selectBackground", PRIMARIO)

    e = ttk.Style(raiz)
    e.theme_use("clam")
    e.configure(".", background=TARJETA, foreground=TEXTO, bordercolor=BORDE,
                lightcolor=BORDE, darkcolor=BORDE, troughcolor=SUTIL,
                focuscolor=PRIMARIO, selectbackground=PRIMARIO)
    e.configure("Fondo.TFrame", background=FONDO)

    e.configure("TLabelframe", background=TARJETA, bordercolor=BORDE,
                relief="solid", borderwidth=1)
    e.configure("TLabelframe.Label", background=FONDO, foreground=PRIMARIO,
                font=(letra, 10, "bold"))
    e.configure("Suave.TLabel", foreground=CONTORNO)

    for widget in ("TEntry", "TSpinbox", "TCombobox"):
        e.configure(widget, fieldbackground=TARJETA, padding=4, arrowcolor=PRIMARIO)
        e.map(widget, bordercolor=[("focus", PRIMARIO)], lightcolor=[("focus", PRIMARIO)],
              fieldbackground=[("disabled", SUTIL), ("readonly", TARJETA)],
              foreground=[("disabled", CONTORNO)])

    e.configure("TButton", background=SUTIL, padding=(12, 6))
    e.map("TButton", background=[("disabled", SUTIL), ("active", BORDE)],
          foreground=[("disabled", CONTORNO)])
    e.configure("Primario.TButton", background=PRIMARIO, foreground="white",
                bordercolor=PRIMARIO, font=(letra, 10, "bold"), padding=(16, 8))
    e.map("Primario.TButton",
          background=[("disabled", PRIMARIO_APAGADO), ("active", PRIMARIO_OSCURO)],
          foreground=[("disabled", "white")])
    e.configure("TCheckbutton", indicatorcolor=TARJETA)
    e.map("TCheckbutton", indicatorcolor=[("selected", PRIMARIO)])

    e.configure("Horizontal.TProgressbar", background=ACENTO, bordercolor=BORDE,
                lightcolor=ACENTO, darkcolor=ACENTO, thickness=14)
    e.configure("Vertical.TScrollbar", background=SUTIL, arrowcolor=CONTORNO)

    e.configure("Encabezado.TFrame", background=PRIMARIO)
    e.configure("Titulo.TLabel", background=PRIMARIO, foreground="white",
                font=(letra, 17, "bold"))
    e.configure("Subtitulo.TLabel", background=PRIMARIO, foreground="#cfe0f3")
    e.configure("Chip.TLabel", background=ACENTO, foreground=SOBRE_ACENTO,
                font=(letra, 9, "bold"), padding=(10, 3))
    e.configure("Treeview", rowheight=26, fieldbackground=TARJETA)
    e.map("Treeview", background=[("selected", PRIMARIO)],
          foreground=[("selected", "white")])
    e.configure("Treeview.Heading", background=SUTIL, foreground=TEXTO_SUAVE,
                font=(letra, 9, "bold"))
