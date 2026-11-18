"""Carga de redes StyleGAN2-ADA desde archivos .pkl.

Es el único módulo que sabe cómo está empaquetado un modelo de NVIDIA.
torch se importa al cargar, no al importar el módulo.
"""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from config import ConfigModelo


# 1. Modelo listo para generar

@dataclass(frozen=True)
class ModeloCargado:
    """La red G_ema en evaluación, su dispositivo y, si aplica, la dirección W+."""
    red: Any
    dispositivo: Any
    direccion: Any = None


# 2. Cargador

class CargadorModelo:
    """Abre el .pkl, elige CPU o GPU y valida el modelo contra config.py.

    El pickle referencia los paquetes dnnlib y torch_utils, por eso la
    carpeta del repositorio de StyleGAN2-ADA debe estar en sys.path.
    """

    def __init__(self, carpeta_modelos: Path, carpeta_stylegan: Path,
                 dispositivo: Optional[str] = None):
        self._carpeta_modelos = Path(carpeta_modelos)
        self._carpeta_stylegan = Path(carpeta_stylegan)
        self._dispositivo = dispositivo

    def cargar(self, config: ConfigModelo) -> ModeloCargado:
        ruta = self._carpeta_modelos / config.archivo
        if not ruta.is_file():
            raise FileNotFoundError(f"No se encontró el modelo {config.codigo}: {ruta}")
        legacy = self._importar_stylegan()

        import torch
        dispositivo = torch.device(self._resolver_dispositivo(torch))
        with open(ruta, "rb") as f:
            red = legacy.load_network_pkl(f)["G_ema"]
        red = red.eval().requires_grad_(False).to(dispositivo)
        if config.metodo == "direccion":
            direccion = self._cargar_direccion(red, config, torch, dispositivo)
            return ModeloCargado(red, dispositivo, direccion)
        if config.metodo == "incondicional":
            self._validar_incondicional(red, config)
            return ModeloCargado(red, dispositivo)
        self._validar_clases(red, config)
        return ModeloCargado(red, dispositivo)

    # 3. Auxiliares

    def _importar_stylegan(self):
        if not (self._carpeta_stylegan / "legacy.py").is_file():
            raise FileNotFoundError(
                "No se encontró el repositorio de StyleGAN2-ADA en "
                f"{self._carpeta_stylegan}. Clónelo o indique su ruta con "
                "--stylegan o STYLEGAN_PATH.")
        carpeta = str(self._carpeta_stylegan.resolve())
        if carpeta not in sys.path:
            sys.path.insert(0, carpeta)
        import legacy
        return legacy

    def _resolver_dispositivo(self, torch) -> str:
        if self._dispositivo:
            return self._dispositivo
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _cargar_direccion(self, red: Any, config: ConfigModelo, torch, dispositivo):
        """Lee el .npy de la dirección W+ con la forma [num_ws, w_dim] de la red."""
        if red.c_dim != 0:
            raise ValueError(f"El modelo {config.codigo} es condicional: "
                             'use metodo="clases" en config.py.')
        faltan = set(config.grados) - set(config.alphas)
        if faltan:
            raise ValueError(f"Faltan alphas en config.py para: {', '.join(sorted(faltan))}")
        ruta = self._carpeta_modelos / config.direccion
        if not ruta.is_file():
            raise FileNotFoundError(f"No se encontró la dirección de {config.codigo}: {ruta}")
        import numpy as np
        valores = np.load(ruta).reshape(red.num_ws, red.w_dim)
        return torch.tensor(valores, dtype=torch.float32, device=dispositivo)

    @staticmethod
    def _validar_incondicional(red: Any, config: ConfigModelo) -> None:
        if red.c_dim != 0:
            raise ValueError(f"El modelo {config.codigo} es condicional: "
                             'use metodo="clases" en config.py.')
        if len(config.grados) != 1:
            raise ValueError(f"El modelo {config.codigo} es de una sola clase: "
                             "declare un único grado o use una dirección.")

    @staticmethod
    def _validar_clases(red: Any, config: ConfigModelo) -> None:
        if red.c_dim == 0:
            raise ValueError(f"El modelo {config.codigo} es incondicional: "
                             'use metodo="incondicional" o "direccion" en config.py.')
        if red.c_dim != len(config.grados):
            raise ValueError(
                f"El modelo {config.codigo} tiene {red.c_dim} clases y "
                f"config.py declara {len(config.grados)} grados.")
