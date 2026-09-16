"""Utilidades compartidas del proyecto MCDI500 - Grupo 5.

Este modulo lo genera el cuaderno de la Fase 1 y lo importan las fases siguientes.
Conjunto: permisos de uso de via publica de San Francisco (DataSF, x8nh-xzn6).
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

MARCADORES = (".git", "requirements.txt", ".gitignore")

FORMATO_FECHA = "%m/%d/%Y"
FORMATO_SELLO = "%Y/%m/%d %I:%M:%S %p"
COLS_FECHA = ["Approved Date", "permit_start_date", "permit_end_date"]
COLS_COORDENADA = ["Latitude", "Longitude"]

# Columnas descartadas y su motivo. Ver seccion 5.2 del cuaderno de la Fase 1.
DESCARTES = {
    "CurbRampWork": "96,4% de nulos y un unico valor distinto: varianza cero",
    "bpa": "95,7% de nulos",
    "permit_address": "63,1% de nulos; redundante con streetname y cross streets",
    "Location": "geometria en texto, redundante con Latitude y Longitude",
    "the_geom": "geometria en texto, redundante con Latitude y Longitude",
    "X": "mismo punto en California State Plane; redundante",
    "Y": "mismo punto en California State Plane; redundante",
    "data_loaded_at": "sello de carga del portal, sin valor analitico",
    "Permit Type": "reemplazada por tipo_permiso agrupado",
    "Agent": "reemplazada por agente agrupado",
    "supervisor_district": "reemplazada por distrito como categorica",
    "AgentPhone": "dato de contacto, sin valor analitico",
    "24/7 Contact": "dato de contacto, sin valor analitico",
    "cnn": "identificador de segmento vial, sin valor explicativo",
}


class ProyectoError(Exception):
    """Error propio del proyecto: permite distinguirlo de los de las librerias."""


def normalizar_nombre(texto):
    """Convierte un nombre de columna a minusculas, sin espacios ni signos.

    Ejemplo
    -------
    >>> normalizar_nombre('Permit Type ')
    'permit_type'
    """
    if not isinstance(texto, str):
        raise ProyectoError(f"Se esperaba texto y se recibio {type(texto).__name__}.")
    limpio = texto.strip().lower()
    limpio = re.sub(r"[^a-z0-9]+", "_", limpio)   # todo lo que no sea letra o digito -> _
    return limpio.strip("_")


def normalizar_columnas(nombres):
    """Aplica normalizar_nombre a una lista y verifica que no se produzcan duplicados."""
    normalizados = [normalizar_nombre(n) for n in nombres]
    if len(set(normalizados)) != len(normalizados):
        raise ProyectoError("La normalizacion produjo nombres duplicados.")
    return normalizados


def localizar_raiz(inicio=None, marcadores=MARCADORES, niveles=5, respaldo=True):
    """Resuelve la raiz del proyecto. Ver seccion 3 del cuaderno de la Fase 1."""
    actual = Path(inicio or Path.cwd()).resolve()
    for candidata in [actual, *actual.parents][:niveles + 1]:
        if any((candidata / m).exists() for m in marcadores):
            return candidata, "estructurado"
    if respaldo:
        return actual, "plano"
    raise FileNotFoundError(f"No se encontro marcador de repositorio desde {actual}.")


def buscar_archivo(nombre, raiz=None, extra=()):
    """Busca un archivo en las ubicaciones canonicas y junto al cuaderno."""
    base = Path(raiz) if raiz is not None else localizar_raiz()[0]
    candidatos = [
        Path.cwd() / nombre, base / nombre,
        base / "data" / "raw" / nombre, base / "data" / "processed" / nombre,
        base / "docs" / nombre, *[Path(d) / nombre for d in extra],
    ]
    vistos = set()
    for ruta in candidatos:
        clave = str(ruta.resolve())
        if clave in vistos:
            continue
        vistos.add(clave)
        if ruta.exists():
            return ruta.resolve()
    return None


def leer_crudo(ruta):
    """Lee el CSV como texto, sin inferencia de tipos.

    La inferencia automatica es inaceptable en esta fuente: las coordenadas usan coma
    decimal y una parte de las fechas admite dos lecturas. Leer todo como texto obliga
    a declarar cada conversion de forma explicita.
    """
    return pd.read_csv(ruta, dtype=str)


def convertir_tipos(datos):
    """Convierte coordenadas, fechas y centinelas. No elimina filas ni columnas."""
    d = datos.copy()
    for col in COLS_COORDENADA:
        if col in d.columns:
            d[col] = pd.to_numeric(d[col].str.replace(",", ".", regex=False), errors="coerce")
    for col in COLS_FECHA:
        if col in d.columns:
            d[col] = pd.to_datetime(d[col], format=FORMATO_FECHA, errors="coerce")
    if "data_as_of" in d.columns:
        d["data_as_of"] = pd.to_datetime(d["data_as_of"], format=FORMATO_SELLO, errors="coerce")
    if "permit_zipcode" in d.columns:
        d["permit_zipcode"] = d["permit_zipcode"].replace("0", np.nan)   # centinela
    return d


def derivar_variables(datos, n_tipos=12, n_agentes=12):
    """Deriva el objetivo y las variables explicativas de la pregunta.

    Lanza
    -----
    KeyError
        Si falta alguna de las columnas necesarias para derivar.
    """
    requeridas = {"permit_start_date", "permit_end_date", "Approved Date",
                  "Permit Type", "Agent", "supervisor_district", "permit_number"}
    faltan = requeridas - set(datos.columns)
    if faltan:
        raise KeyError(f"Faltan columnas para derivar: {sorted(faltan)}")

    d = datos.copy()
    d["duracion_dias"] = (d["permit_end_date"] - d["permit_start_date"]).dt.days
    d["n_segmentos"] = d.groupby("permit_number")["permit_number"].transform("size")
    d["lag_aprob_inicio"] = (d["permit_start_date"] - d["Approved Date"]).dt.days
    d["anio_aprobacion"] = d["Approved Date"].dt.year
    d["mes_inicio"] = d["permit_start_date"].dt.month

    principales_tipo = d["Permit Type"].value_counts().head(n_tipos).index
    d["tipo_permiso"] = np.where(d["Permit Type"].isin(principales_tipo),
                                 d["Permit Type"], "Otros")
    principales_agente = d["Agent"].value_counts().head(n_agentes).index
    d["agente"] = np.where(d["Agent"].isin(principales_agente),
                           d["Agent"].fillna("Desconocido"), "Otros")
    d["distrito"] = d["supervisor_district"].fillna("Desconocido").astype(str)
    return d


def construir_conjunto_trabajo(datos_crudos):
    """Aplica el plan de saneamiento completo: tipos, derivadas, descartes y filtros.

    Implementa la decision justificada en la seccion 5.2 del cuaderno de la Fase 1.
    """
    d = derivar_variables(convertir_tipos(datos_crudos))
    d = d.drop(columns=[c for c in DESCARTES if c in d.columns])
    d = d.dropna(subset=["duracion_dias"])      # sin objetivo no hay caso analizable
    d = d.drop_duplicates()
    return d.reset_index(drop=True)


def clasificar_rol(serie):
    """Asigna el rol analitico de una variable segun las reglas del curso."""
    s = serie.dropna()
    if s.empty:
        return "vacia"
    unicos = s.nunique()
    proporcion = unicos / len(s)
    es_numerica = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
    if pd.api.types.is_datetime64_any_dtype(s):
        return "fecha"
    if unicos == 2:
        return "binaria"
    if es_numerica:
        entera = s.mod(1).eq(0).all()
        if entera and proporcion > 0.95 and len(s) > 50:
            return "identificador"
        if entera and (unicos <= 20 or proporcion < 0.05):
            return "discreta"
        return "continua"
    if pd.to_datetime(s.head(200), errors="coerce", format="mixed").notna().mean() > 0.9:
        return "fecha"
    if s.astype(str).str.len().mean() > 60:
        return "texto libre"
    if proporcion > 0.95 and len(s) > 50:
        return "identificador"
    return "nominal" if unicos <= 15 else "alta cardinalidad"


def contar_roles(datos):
    """Cuenta variables por rol analitico."""
    return pd.Series([clasificar_rol(datos[c]) for c in datos.columns]).value_counts().to_dict()


def perfilar(datos):
    """Devuelve rol, dtype, nulos y cardinalidad por columna."""
    return pd.DataFrame({
        "rol": [clasificar_rol(datos[c]) for c in datos.columns],
        "dtype": datos.dtypes.astype(str),
        "n_nulos": datos.isna().sum(),
        "pct_nulos": (datos.isna().mean() * 100).round(2),
        "n_unicos": datos.nunique(dropna=True),
    }, index=datos.columns)
