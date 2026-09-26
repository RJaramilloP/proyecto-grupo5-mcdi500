# Factores asociados a la duración de los permisos de uso de vía pública en San Francisco


## Integrantes

- Marco Álvarez Araya ([@Marco30101994-Unab](https://github.com/Marco30101994-Unab))
- María Fassler Neumann ([@belenfassler](https://github.com/belenfassler))
- Ricardo Jaramillo Pulgar ([@RJaramilloP](https://github.com/RJaramilloP))

## Pregunta de investigación

¿Qué factores se asocian con la duración autorizada de los permisos vigentes de uso de vía pública en San Francisco al 9 de septiembre de 2026, medida como el número de días entre las fechas de inicio y término del permiso, considerando el tipo de permiso, el barrio de emplazamiento, el agente y el año de aprobación?

El proyecto tiene un alcance descriptivo y asociativo. Por lo tanto, sus resultados no deben interpretarse como relaciones causales.

## Datos utilizados

Los datos provienen del conjunto [Active Street-Use Permits](https://data.sf.gov/City-Infrastructure/Active-Street-Use-Permits/x8nh-xzn6/about_data), publicado por San Francisco Public Works en DataSF.

- Fecha de la data: 9 de septiembre de 2026.
- Licencia: PDDL 1.0.
- Archivo original: `data/raw/Active_Street-Use_Permits_20260909.csv`.
- Conjunto de trabajo: 6.010 registros y 2.139 permisos.
- Unidad de observación: segmento de calle.
- Unidad de análisis definida en Fase 3: permiso.

El archivo original se conserva sin modificaciones. Debido a que la fuente se actualiza diariamente, volver a descargarla podría producir resultados diferentes.

### Limitación

La fuente contiene solamente permisos vigentes en la fecha de corte. Esto puede sobrerrepresentar los permisos de mayor duración. En consecuencia, los resultados describen los permisos activos al 9 de septiembre de 2026 y no la totalidad histórica de permisos otorgados.

## Desarrollo del proyecto

- **Fase 1:** definición del problema, entorno reproducible y documentación de los datos.
- **Fase 2:** limpieza, transformación, imputación, codificación y escalamiento.
- **Fase 3:** reorganización del pipeline mediante programación orientada a objetos, evaluación de eficiencia, validaciones y definición de la unidad de análisis.
- **Fase 4:** análisis final, interpretación y comunicación de resultados.

## Estructura del repositorio

```text
F1/                 notebooks de la Fase 1
F2/                 notebooks de la Fase 2
F3/                 notebook de la Fase 3
F4/                 archivos de la Fase 4
data/raw/           datos originales
data/processed/     conjuntos procesados
src/                módulos reutilizables
artefactos/         objetos ajustados
docs/               metadatos, resultados y anexos
```

La carpeta `src/` contiene solamente código fuente. Los archivos serializados se guardan en `artefactos/`.

## Instalación

Crear y activar un entorno virtual:

### Linux o macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Luego, iniciar Jupyter:

```bash
jupyter lab
```

Las versiones oficiales de las dependencias se encuentran en `requirements.txt`.

## Ejecución

Los notebooks deben ejecutarse desde la raíz del repositorio y en el siguiente orden:

1. Fase 1.
2. Fase 2.
3. `F3/S2_F3_NucleoAlgoritmico_Eficiencia_POO.ipynb`.

En cada notebook se recomienda utilizar:

**Kernel → Restart Kernel and Run All Cells**

La ejecución de Fase 3 debe terminar sin errores y generar los conjuntos procesados, parámetros, mediciones de eficiencia, metadatos y anexos correspondientes.

## Decisiones técnicas principales

- Semilla aleatoria fijada en 42.
- Fechas convertidas mediante formatos declarados explícitamente.
- Partición agrupada por `permit_number`.
- Ajuste de transformaciones solamente con datos de entrenamiento.
- Un permiso por fila como unidad principal de análisis.
- Comparación reproducible de implementaciones mediante tiempo y memoria.
- Organización modular mediante clases, transformadores y un pipeline reutilizable.

## Convención de commits

Se utilizan los prefijos:

- `feat`: nuevas funcionalidades;
- `fix`: correcciones;
- `data`: datos y transformaciones;
- `test`: pruebas;
- `perf`: eficiencia;
- `docs`: documentación;
- `refactor`: reorganización del código.

Las contribuciones pueden verificarse mediante:

```bash
git shortlog -sne HEAD
```