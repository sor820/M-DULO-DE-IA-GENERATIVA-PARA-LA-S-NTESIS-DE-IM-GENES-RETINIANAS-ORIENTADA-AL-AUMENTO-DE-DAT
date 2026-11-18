"""Punto de entrada de RetinaSynth.

Es el único lugar donde se eligen las clases concretas y se arman las
dependencias. Con --simulado la aplicación corre sin torch ni .pkl.
"""
import argparse
import time
import tkinter as tk
from pathlib import Path

import config
from interfaz.ventana import VentanaPrincipal
from nucleo.almacenamiento import RepositorioImagenes
from nucleo.balanceo import AnalizadorDataset
from nucleo.generador import (GeneradorDireccion, GeneradorIncondicional,
                              GeneradorSimulado, GeneradorStyleGAN)
from nucleo.modelo import CargadorModelo
from nucleo.servicio import ServicioSintesis


# 1. Argumentos de línea de comandos

def leer_argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Síntesis de retinografías por grado.")
    p.add_argument("--simulado", action="store_true",
                   help="usar el generador de ruido (sin GPU ni .pkl)")
    p.add_argument("--modelos", type=Path, default=config.CARPETA_MODELOS,
                   help="carpeta con los archivos .pkl")
    p.add_argument("--stylegan", type=Path, default=config.CARPETA_STYLEGAN,
                   help="carpeta del repositorio stylegan2-ada-pytorch")
    p.add_argument("--salida", type=Path, default=config.CARPETA_SALIDA,
                   help="carpeta de salida propuesta en la ventana")
    p.add_argument("--dispositivo", default=None,
                   help="cpu, cuda o cuda:N (por omisión, GPU si hay)")
    p.add_argument("--prueba", metavar="MODELO", choices=list(config.MODELOS),
                   help="sin ventana: cargar el .pkl, generar unas imágenes y medir")
    return p.parse_args()


# 2. Prueba de humo: el .pkl carga y genera

def prueba_humo(config_modelo: config.ConfigModelo, generador) -> None:
    """Mide la carga y la velocidad; aquí aparecen los avisos de los kernels."""
    grado = config_modelo.grados[0]
    psi = config_modelo.truncation_de(grado)
    inicio = time.perf_counter()
    primera = next(iter(generador.generar(grado, 1, psi, 0)))
    carga = time.perf_counter() - inicio
    inicio = time.perf_counter()
    for _ in generador.generar(grado, 5, psi, 1):
        pass
    por_imagen = (time.perf_counter() - inicio) / 5
    print(f"{config_modelo.codigo}/{grado}: {primera.imagen.size[0]}x"
          f"{primera.imagen.size[1]} px; carga y primera imagen {carga:.1f} s; "
          f"después {por_imagen:.2f} s por imagen")


# 3. Ensamble

def main() -> None:
    args = leer_argumentos()
    if args.simulado:
        fabrica_generador = GeneradorSimulado
    else:
        cargador = CargadorModelo(args.modelos, args.stylegan, args.dispositivo)
        por_metodo = {"clases": GeneradorStyleGAN, "direccion": GeneradorDireccion,
                      "incondicional": GeneradorIncondicional}
        fabrica_generador = lambda cfg: por_metodo[cfg.metodo](cfg, cargador)

    if args.prueba:
        cfg = config.MODELOS[args.prueba]
        prueba_humo(cfg, fabrica_generador(cfg))
        return

    servicio = ServicioSintesis(config.MODELOS, fabrica_generador,
                                RepositorioImagenes, AnalizadorDataset())
    raiz = tk.Tk()
    VentanaPrincipal(raiz, servicio, config.MODELOS, args.salida, args.simulado)
    raiz.mainloop()


if __name__ == "__main__":
    main()
