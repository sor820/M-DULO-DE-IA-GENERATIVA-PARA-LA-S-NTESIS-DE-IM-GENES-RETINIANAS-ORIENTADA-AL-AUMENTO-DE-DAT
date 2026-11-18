"""Análisis de desbalance de un dataset organizado por carpetas.

Cuenta imágenes por clase y calcula cuántas sintéticas faltan a cada una
para igualar a la clase mayoritaria.
"""
from pathlib import Path

from config import EXTENSIONES_IMAGEN
from nucleo.contratos import AnalisisDataset


# 1. Analizador

class AnalizadorDataset:
    """Recorre <dataset>/<clase>/ y compara contra los grados configurados.

    Los nombres de carpeta se comparan sin distinguir mayúsculas; un grado
    sin carpeta cuenta como cero imágenes.
    """

    def analizar(self, carpeta: Path, grados: tuple[str, ...]) -> AnalisisDataset:
        carpeta = Path(carpeta)
        if not carpeta.is_dir():
            raise FileNotFoundError(f"No existe la carpeta de dataset: {carpeta}")

        por_nombre = {g.lower(): g for g in grados}
        conteo = {g: 0 for g in grados}
        ignoradas = []
        for sub in sorted(p for p in carpeta.iterdir() if p.is_dir()):
            grado = por_nombre.get(sub.name.lower())
            if grado is None:
                ignoradas.append(sub.name)
            else:
                conteo[grado] += self._contar_imagenes(sub)

        if not any(conteo.values()):
            raise ValueError("Ninguna carpeta del dataset coincide con los "
                             f"grados configurados: {', '.join(grados)}")
        return AnalisisDataset(conteo, self._faltantes(conteo), ignoradas)

    @staticmethod
    def _contar_imagenes(carpeta: Path) -> int:
        return sum(1 for p in carpeta.iterdir()
                   if p.is_file() and p.suffix.lower() in EXTENSIONES_IMAGEN)

    @staticmethod
    def _faltantes(conteo: dict[str, int]) -> dict[str, int]:
        objetivo = max(conteo.values())
        return {g: objetivo - n for g, n in conteo.items()}
