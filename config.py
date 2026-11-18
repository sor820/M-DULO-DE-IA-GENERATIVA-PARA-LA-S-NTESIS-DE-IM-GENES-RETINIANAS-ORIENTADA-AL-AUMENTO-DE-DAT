"""Catálogo declarativo de RetinaSynth.

Dar de alta un modelo nuevo es agregar una entrada a MODELOS; ningún otro
archivo cambia. Aquí no hay lógica, solo datos.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# 1. Descripción de un modelo generativo

@dataclass(frozen=True)
class ConfigModelo:
    """Un modelo StyleGAN2-ADA y cómo se obtiene cada grado de severidad.

    metodo "clases": modelo condicional; el grado i es la posición i del
    one-hot, en el mismo orden con que se entrenó.
    metodo "direccion": modelo incondicional; el grado es un desplazamiento
    alpha a lo largo de una dirección fija en W+ (archivo .npy).
    metodo "incondicional": modelo de una sola clase (un único grado).
    """
    codigo: str
    nombre: str
    archivo: str
    grados: tuple[str, ...]
    truncation: dict[str, float]
    metodo: str = "clases"
    direccion: Optional[str] = None
    alphas: dict[str, float] = field(default_factory=dict)

    def truncation_de(self, grado: str) -> float:
        return self.truncation.get(grado, TRUNCATION_PREDETERMINADA)


# 2. Catálogo de modelos disponibles

TRUNCATION_PREDETERMINADA = 0.7

MODELOS: dict[str, ConfigModelo] = {
    "RD": ConfigModelo(
        codigo="RD",
        nombre="Retinopatía diabética",
        archivo="rd/RD_primer_modelo.pkl",
        grados=("No_DR", "Leve", "Moderado", "Grave", "Proliferativa"),
        truncation={"No_DR": 0.5, "Leve": 0.6, "Moderado": 0.7,
                    "Grave": 0.85, "Proliferativa": 1.0},
    ),
    "DMAE": ConfigModelo(
        codigo="DMAE",
        nombre="Degeneración macular asociada a la edad",
        archivo="dmae/Copia de network-snapshot-000168.pkl",
        grados=("Sano", "Leve", "Moderado", "Severo"),
        truncation={"Sano": 0.5, "Leve": 0.6, "Moderado": 0.7, "Severo": 0.8},
    ),
    "RH": ConfigModelo(
        codigo="RH",
        nombre="Retinopatía hipertensiva",
        archivo="rh/retinopatia_hipertensiva.pkl",
        grados=("Grado_I", "Grado_II", "Grado_III", "Grado_IV"),
        truncation={"Grado_I": 0.7, "Grado_II": 0.7,
                    "Grado_III": 0.7, "Grado_IV": 0.7},
        metodo="direccion",
        direccion="rh/direccion_hr_wplus.npy",
        alphas={"Grado_I": 0, "Grado_II": 10, "Grado_III": 20, "Grado_IV": 30},
    ),
    "SANO": ConfigModelo(
        codigo="SANO",
        nombre="Ojos sanos",
        archivo="sanos/sano_modelo_2.pkl",
        grados=("Sano",),
        truncation={"Sano": 0.7},
        metodo="incondicional",
    ),
}


# 3. Rutas: relativas al proyecto, o las que fije el entorno (Docker)

RAIZ = Path(__file__).resolve().parent
CARPETA_MODELOS = Path(os.environ.get("MODELOS_PATH", RAIZ / "modelos"))
CARPETA_SALIDA = Path(os.environ.get("SALIDA_PATH", RAIZ / "salida"))
CARPETA_STYLEGAN = Path(os.environ.get("STYLEGAN_PATH",
                                       RAIZ / "stylegan2-ada-pytorch"))

EXTENSIONES_IMAGEN = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
NOMBRE_MANIFIESTO = "manifiesto.csv"
