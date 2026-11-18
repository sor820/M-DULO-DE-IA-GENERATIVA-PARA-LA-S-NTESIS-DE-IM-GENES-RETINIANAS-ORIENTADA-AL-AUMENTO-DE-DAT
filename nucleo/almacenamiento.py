"""Escritura de las imágenes sintéticas y de su manifiesto.

Una carpeta por clase, PNG con numeración consecutiva y una fila del
manifiesto por imagen. Si la carpeta ya existe, se continúa donde quedó.
"""
import csv
import re
from datetime import datetime
from pathlib import Path

from config import NOMBRE_MANIFIESTO
from nucleo.contratos import ResultadoImagen

COLUMNAS = ("archivo", "modelo", "clase", "semilla", "truncation", "fecha")


# 1. Repositorio de imágenes en disco

class RepositorioImagenes:
    """Guarda en <raiz>/<clase>/<modelo>_<clase>_NNNN.png y anota el CSV."""

    def __init__(self, raiz: Path):
        self._raiz = Path(raiz)
        self._raiz.mkdir(parents=True, exist_ok=True)
        self._contadores: dict[tuple[str, str], int] = {}
        ruta_csv = self._raiz / NOMBRE_MANIFIESTO
        nuevo = not ruta_csv.exists() or ruta_csv.stat().st_size == 0
        self._archivo = open(ruta_csv, "a", newline="", encoding="utf-8")
        self._csv = csv.writer(self._archivo)
        if nuevo:
            self._csv.writerow(COLUMNAS)
            self._archivo.flush()

    def guardar(self, resultado: ResultadoImagen) -> Path:
        carpeta = self._raiz / resultado.clase
        carpeta.mkdir(exist_ok=True)
        prefijo = f"{resultado.modelo}_{resultado.clase}".lower()
        numero = self._siguiente_numero(carpeta, prefijo)
        ruta = carpeta / f"{prefijo}_{numero:04d}.png"
        resultado.imagen.save(ruta, format="PNG")
        self._anotar(ruta, resultado)
        return ruta

    def cerrar(self) -> None:
        if not self._archivo.closed:
            self._archivo.close()

    def __enter__(self) -> "RepositorioImagenes":
        return self

    def __exit__(self, *_) -> None:
        self.cerrar()

    # 2. Numeración y manifiesto

    def _siguiente_numero(self, carpeta: Path, prefijo: str) -> int:
        """Busca el último número en disco solo la primera vez por clase."""
        clave = (str(carpeta), prefijo)
        if clave not in self._contadores:
            patron = re.compile(rf"^{re.escape(prefijo)}_(\d+)\.png$")
            usados = [int(m.group(1)) for p in carpeta.iterdir()
                      if (m := patron.match(p.name.lower()))]
            self._contadores[clave] = max(usados, default=0)
        self._contadores[clave] += 1
        return self._contadores[clave]

    def _anotar(self, ruta: Path, r: ResultadoImagen) -> None:
        """Una fila por imagen, escrita al momento: cancelar no deja huecos."""
        relativa = ruta.relative_to(self._raiz).as_posix()
        fecha = datetime.now().isoformat(timespec="seconds")
        self._csv.writerow((relativa, r.modelo, r.clase, r.semilla,
                            r.truncation, fecha))
        self._archivo.flush()
