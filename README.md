# RetinaSynth

Herramienta de escritorio para sintetizar retinografías por grado de
severidad con StyleGAN2-ADA condicional, y dejarlas organizadas para
entrenar un clasificador.

- Genera N imágenes de un grado concreto (retinopatía diabética o DMAE).
- **Modo balanceo:** analiza un dataset real organizado por carpetas y genera
  las imágenes que faltan a cada grado para igualar a la clase mayoritaria.
- Cada imagen queda registrada en `manifiesto.csv` con su semilla y truncation,
  para poder regenerarla.

## Modelos disponibles

| Código | Enfermedad | Grados |
|---|---|---|
| RD | Retinopatía diabética | No_DR, Leve, Moderado, Grave, Proliferativa |
| DMAE | Degeneración macular asociada a la edad | Sano, Leve, Moderado, Severo |
| RH | Retinopatía hipertensiva | Grado_I, Grado_II, Grado_III, Grado_IV |
| SANO | Ojos sanos | Sano |

El catálogo está en `config.py`. Para agregar una enfermedad basta con añadir
una entrada a `MODELOS`. Hay tres métodos:

- **`clases`** (RD, DMAE): el modelo es condicional y el grado entra como
  one-hot. El orden de `grados` debe coincidir con el de las etiquetas con que
  se entrenó.
- **`direccion`** (RH): el modelo es incondicional (`c_dim = 0`). Cada grado se
  obtiene desplazando el vector latente por una dirección fija en W+ (el `.npy`,
  extraída con un SVM entre pacientes con y sin la enfermedad):
  `w = mapping(z) + alpha · dirección`, con alpha = 0, 10, 20 y 30. Por eso el
  grado de una imagen de RH no es una etiqueta aprendida por la red, sino la
  intensidad del desplazamiento. Más allá de alpha ≈ 30 la imagen se degrada.
- **`incondicional`** (SANO): modelo de una sola clase, entrenado solo con
  retinas sanas; se genera con `G(z, None, ψ)`. Sirve para completar la clase
  normal de un dataset.

### Grado y truncation no son lo mismo

- **El grado es la condición clínica**: decide qué enfermedad, y con qué
  severidad, aparece en la imagen. En RD y DMAE es la etiqueta que se le pasa a
  la red (`G(z, etiqueta, ψ)`); en RH es el alpha de la dirección.
- **La truncation (ψ) es un control de calidad y diversidad**: acerca el vector
  latente al promedio de lo que aprendió la red. Con ψ bajo (≈ 0.5) las
  imágenes salen limpias y parecidas entre sí, con pocos artefactos. Con ψ alto
  (≈ 1.0) salen más variadas, pero aparecen más imágenes defectuosas. No cambia
  el grado: «Leve» con ψ 0.9 sigue siendo leve, solo que más variado.

Cada grado trae un ψ sugerido, tomado de la tesis, que la ventana pone en el
campo *Truncation ψ* al elegirlo y que se puede cambiar:

| Modelo | Qué define el grado | ψ sugerido |
|---|---|---|
| RD | Etiqueta (one-hot) | No_DR 0.5 · Leve 0.6 · Moderado 0.7 · Grave 0.85 · Proliferativa 1.0 |
| DMAE | Etiqueta (one-hot) | Sano 0.5 · Leve 0.6 · Moderado 0.7 · Severo 0.8 |
| RH | Alpha en W+ (0, 10, 20, 30) | 0.7 en todos los grados |
| SANO | Hay un solo grado | 0.7 |

El ψ sube con la severidad porque las lesiones de los grados graves
(hemorragias, drusas grandes, neovasos) son muy variadas. Con ψ bajo se
«aplanan» hacia el promedio y se pierden. Los grados sanos o leves usan ψ bajo
para salir limpios. En RH, la truncation queda fija en 0.7 y la severidad la da
solo el alpha.

## Lo que no viene en el repositorio

### StyleGAN2-ADA (NVIDIA)

RetinaSynth **no incluye** StyleGAN2-ADA. Es software de NVIDIA, se clona por
separado y su licencia (*NVIDIA Source Code License-NC*) **solo permite el uso
no comercial**. Los `.pkl` necesitan sus paquetes `dnnlib` y `torch_utils` para
abrirse.

```bash
git clone https://github.com/NVlabs/stylegan2-ada-pytorch
```

Se clona dentro de la carpeta del proyecto. Está en `.gitignore`, así que no
se versiona.

### Modelos entrenados

Los archivos `.pkl` son los generadores entrenados para este proyecto y no se
distribuyen en el repositorio porque pesan unos 300 MB cada uno. Copie a
`modelos/` los archivos que declara `config.py`:

```
retinasynth/
├── modelos/
│   ├── rd/RD_primer_modelo.pkl
│   ├── dmae/Copia de network-snapshot-000168.pkl
│   ├── rh/retinopatia_hipertensiva.pkl + direccion_hr_wplus.npy
│   └── sanos/sano_modelo_2.pkl
├── stylegan2-ada-pytorch/   clonado de NVIDIA
└── salida/                  se crea al generar
```

## Ejecución con Docker (recomendada)

Requiere Docker Desktop con soporte de GPU de NVIDIA y WSLg (Windows 11), que es
lo que lleva la ventana de Tkinter del contenedor al escritorio de Windows.
Desde PowerShell, en la carpeta del proyecto:

```bash
docker compose build     # solo la primera vez o al cambiar el Dockerfile
docker compose up -d     # abre la ventana
```

También se puede arrancar con el botón ▶ del proyecto en Docker Desktop. Al
cerrar la ventana, el contenedor se detiene. Como el código está montado como
volumen, los cambios en Python se ven en el siguiente arranque sin reconstruir.

Si se lanza desde una terminal WSL (Ubuntu), antes hay que indicar dónde está
el socket de la pantalla: `export X11_SOCKET=/mnt/wslg/.X11-unix`.

Si la GPU es de la serie 50 (capability `(12, 0)`), hay que construir con los
`--build-arg` de cu128 que están documentados en el `Dockerfile`.

### Pruebas de humo

En PowerShell, quite las `\` del final de línea y escriba cada comando en una
sola línea. Primero confirme que la ventana se abre (aparece un recuadro que se cierra
solo a los tres segundos):

```bash
docker compose run --rm retinasynth python -c \
  "import tkinter; r=tkinter.Tk(); r.title('ok'); r.geometry('300x200'); r.after(3000, r.destroy); r.mainloop()"
```

Luego, que se ve la GPU (debe imprimir `True` y la capability):

```bash
docker compose run --rm retinasynth python -c \
  "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))"
```

Por último, que el `.pkl` carga y genera:

```bash
docker compose run --rm retinasynth python main.py --prueba RD
```

Si en esta última aparece un aviso de que no se pudo compilar un *plugin*
(`upfirdn2d`, `bias_act`), StyleGAN2-ADA sigue funcionando con su
implementación de referencia, que es correcta pero más lenta.

## Ejecución local (sin Docker)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
python main.py
```

| Opción | Uso |
|---|---|
| `--simulado` | Genera imágenes de ruido. No carga torch ni los `.pkl`; sirve para probar la interfaz. |
| `--prueba RD\|DMAE\|RH\|SANO` | Ejecuta sin ventana: carga el modelo, genera unas imágenes y mide el tiempo. |
| `--modelos`, `--stylegan`, `--salida` | Cambian las rutas. También se pueden fijar con `MODELOS_PATH`, `STYLEGAN_PATH` y `SALIDA_PATH`. |
| `--dispositivo cpu\|cuda` | Por omisión se usa la GPU si hay una disponible. |

## Salida

```
salida/
├── No_DR/rd_no_dr_0001.png
├── Leve/…
└── manifiesto.csv     archivo,modelo,clase,semilla,truncation,fecha
```

Hay una carpeta por grado, con el mismo nombre que en el catálogo. Es la
estructura que esperan `dataset_tool.py` de StyleGAN2-ADA y `ImageFolder` de
PyTorch. Si la carpeta ya existe, la numeración continúa y el manifiesto se
amplía sin borrar lo anterior.

**Reproducibilidad:** la imagen se genera a partir de la semilla con ruido
constante (`noise_mode='const'`) y en precisión fp32. Con la misma semilla, truncation, modelo y
equipo se obtiene la misma imagen. Entre CPU y GPU puede haber diferencias
mínimas de redondeo.

## Arquitectura

```
nucleo/     síntesis, balanceo y almacenamiento (no importa tkinter)
interfaz/   ventana Tkinter (no importa torch)
main.py     único punto donde se arman las dependencias
```

La generación corre en un hilo aparte y comunica su progreso por una cola,
así que la ventana nunca se congela. Al cancelar, se termina la imagen en
curso y el manifiesto queda consistente con lo que se escribió.
