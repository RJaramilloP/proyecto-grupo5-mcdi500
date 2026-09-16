# Factores asociados a la duración autorizada de los permisos de uso de vía pública en San Francisco — Grupo 5

Los permisos de uso de vía pública regulan la ocupación temporal del espacio público por excavaciones, obras, instalaciones de telecomunicaciones y usos comerciales. La duración autorizada de cada permiso determina cuánto tiempo una calle queda afectada. El problema es de asociación: identificar qué factores se relacionan con esa duración, medida como el número de días entre la fecha de inicio y la de término del permiso.

## Integrantes
- MARCO ÁLVAREZ ARAYA (@Marco30101994-Unab)
- MARÍA FASSLER NEUMANN (@belenfassler)
- RICARDO JARAMILLO PULGAR (@RJaramilloP)

## Pregunta de investigación
¿Qué proporción de la variación en la duración se asocia al tipo de permiso?

## Datos
- Fuente: Active Street-Use Permits — conjunto de trabajo (San Francisco Public Works, DataSF)
- Enlace: https://data.sf.gov/City-Infrastructure/Active-Street-Use-Permits/x8nh-xzn6/about_data
- Licencia: Open Data Commons Public Domain Dedication and License (PDDL) 1.0
- Corte: 2026-09-09 · descargado el 2026-09-09
- Actualización: diaria. El CSV en `data/raw/` ES el dato: volver a
  descargarlo produce un conjunto distinto y rompe la reproducibilidad.
- Conjunto de trabajo: 6010 filas x 23 columnas
- Ubicación esperada: `data/raw/`

## Limitación declarada
La fuente publica solo permisos vigentes, de modo que los de mayor duración quedan
sobrerrepresentados. Las conclusiones describen los permisos vigentes al corte, no la
población de permisos otorgados. El histórico sin ese filtro es `b6tj-gt35`.

## Estructura del repositorio
```
data/raw/        datos originales, sin modificar
data/processed/  datos tras limpieza y transformación (F2)
docs/            diccionario, fichas y metadatos
src/             módulos reutilizables del proyecto
F1/ F2/ F3/ F4/  cuadernos e informes de cada fase
```

## Requisitos y ejecución
    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    python -m pip install -r requirements.txt

Ejecutar los cuadernos en orden: primero F1, después F2.

### Dependencias declaradas
- ipykernel
- jupyterlab
- matplotlib==3.9.4
- notebook
- numpy==2.0.2
- pandas==2.3.3
- scikit-learn==1.6.1

## Convención de commits
Prefijos usados: docs, data, feat, fix.

## Decisiones técnicas
- Los datos son comunes a todas las fases (`data/`); los cuadernos se separan por fase.
- La raíz del proyecto se detecta por marcador, no se asume igual al directorio de lanzamiento.
- Semilla aleatoria fijada en 42 para asegurar reproducibilidad.
- El formato de las fechas se declara de forma explícita y nunca se deduce.
