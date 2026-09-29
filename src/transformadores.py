"""Núcleo algorítmico del proyecto MCDI500 - Grupo 5, Fase 3.

Generado por F3/S2_F3_NucleoAlgoritmico_Eficiencia_POO.ipynb, apartado 17.
No editar a mano: los cambios se hacen en el cuaderno.
"""

import numpy as np
import pandas as pd

import utilidades


# Constantes heredadas de la Fase 1. No se redefinen aquí: se toman del módulo
# compartido, de modo que exista UNA sola declaración de cada una en el proyecto.
FORMATO_FECHA   = utilidades.FORMATO_FECHA      # "%m/%d/%Y", declarado, nunca inferido
FORMATO_SELLO   = utilidades.FORMATO_SELLO
COLS_FECHA      = utilidades.COLS_FECHA
COLS_COORDENADA = utilidades.COLS_COORDENADA
DESCARTES       = utilidades.DESCARTES          # 14 columnas y su motivo


class Transformador:
    """Clase base de todo paso del pipeline. No se usa directamente.

    Define QUE metodos tiene cada paso y CUANDO se ejecutan; las clases hijas
    definen QUE aprende cada uno y COMO lo aplica.

    Contrato doble
    --------------
    Se exponen dos juegos de nombres para la misma maquinaria:

    - ``ajustar`` / ``transformar``: el contrato del material del curso.
    - ``fit`` / ``transform``: la interfaz de scikit-learn, para que los
      objetos ya ajustados de la Fase 2 sigan componiendo sin reescribirse.

    No son dos implementaciones: los segundos delegan en los primeros. La
    equivalencia se mide en la seccion 11 del cuaderno.
    """

    def __init__(self, columnas=None):
        # Atributo publico: parte de la configuracion, cualquiera puede leerlo.
        self.columnas = ([columnas] if isinstance(columnas, str)
                         else list(columnas) if columnas is not None else [])
        # Guion bajo inicial: estado INTERNO. Python no lo impide, pero la
        # convencion avisa a quien lee que no debe tocarse desde fuera.
        self._parametros = {}
        self._ajustado = False

    # ---- lectura controlada del estado ---------------------------------
    @property
    def nombre(self):
        """Identifica al objeto por su clase real, no por la clase base."""
        detalle = ", ".join(self.columnas) if self.columnas else ""
        return f"{type(self).__name__}({detalle})" if detalle else type(self).__name__

    @property
    def parametros(self):
        """Copia defensiva: quien la recibe no puede alterar el estado interno."""
        return dict(self._parametros)

    @property
    def ajustado(self):
        return self._ajustado

    # ---- el ciclo de vida ----------------------------------------------
    def ajustar(self, datos):
        """Aprende los parametros del subconjunto recibido."""
        self.verificar_columnas(datos)
        self._parametros = self.aprender(datos)
        self._ajustado = True
        return self                      # permite encadenar

    def transformar(self, datos):
        """Aplica lo aprendido. Falla si todavia no se ajusto."""
        if not self._ajustado:
            raise RuntimeError(f"{self.nombre}: hay que ajustar antes de transformar.")
        return self.aplicar(datos.copy())   # copia: nunca se altera la entrada

    def ajustar_transformar(self, datos):
        return self.ajustar(datos).transformar(datos)

    # ---- alias con la interfaz de scikit-learn --------------------------
    def fit(self, X, y=None):
        return self.ajustar(X)

    def transform(self, X):
        return self.transformar(X)

    def fit_transform(self, X, y=None):
        return self.ajustar_transformar(X)

    # ---- puntos de extension que cada hija implementa -------------------
    def verificar_columnas(self, datos):
        """Valida la entrada antes de trabajar, para fallar donde se entiende."""
        faltan = [c for c in self.columnas if c not in datos.columns]
        if faltan:
            raise KeyError(f"{self.nombre}: columnas ausentes: {sorted(faltan)}")

    def aprender(self, datos):
        raise NotImplementedError("Cada clase hija debe implementar aprender().")

    def aplicar(self, datos):
        raise NotImplementedError("Cada clase hija debe implementar aplicar().")

    def __repr__(self):
        return f"<{self.nombre} {'ajustado' if self._ajustado else 'sin ajustar'}>"


# =====================================================================
# ETAPA A: antes de la particion (no hay fuga posible)
# =====================================================================


class ConversorTipos(Transformador):
    """Convierte coordenadas, fechas y centinelas con formato declarado.

    Encapsula el hallazgo de la Fase 2: las coordenadas usan coma decimal y el
    formato de fecha admite dos lecturas. `aprender` deja registrado cuanto se
    convirtio, de modo que el diagnostico queda en el estado del objeto.
    """

    def aprender(self, datos):
        registro = {}
        for col in COLS_COORDENADA:
            if col in datos.columns:
                directo = pd.to_numeric(datos[col], errors="coerce").notna().sum()
                con_punto = pd.to_numeric(
                    datos[col].str.replace(",", ".", regex=False), errors="coerce"
                ).notna().sum()
                registro[f"{col}_sin_correccion"] = int(directo)
                registro[f"{col}_con_correccion"] = int(con_punto)
        for col in COLS_FECHA:
            if col in datos.columns:
                explicito = pd.to_datetime(datos[col], format=FORMATO_FECHA,
                                           errors="coerce").notna().sum()
                registro[f"{col}_formato_explicito"] = int(explicito)
        return registro

    def aplicar(self, datos):
        for col in COLS_COORDENADA:
            if col in datos.columns:
                datos[col] = pd.to_numeric(
                    datos[col].str.replace(",", ".", regex=False), errors="coerce")
        for col in COLS_FECHA:
            if col in datos.columns:
                datos[col] = pd.to_datetime(datos[col], format=FORMATO_FECHA,
                                            errors="coerce")
        if "data_as_of" in datos.columns:
            datos["data_as_of"] = pd.to_datetime(datos["data_as_of"],
                                                 format=FORMATO_SELLO, errors="coerce")
        if "permit_zipcode" in datos.columns:
            datos["permit_zipcode"] = datos["permit_zipcode"].replace("0", np.nan)
        return datos


class DerivadorVariables(Transformador):
    """Deriva el objetivo y las explicativas, y agrupa las nominales largas.

    El agrupamiento de `Permit Type` y `Agent` en sus niveles mas frecuentes es
    estado aprendido, no una constante: por eso vive en `_parametros` y no en el
    cuerpo de `aplicar`.
    """

    REQUERIDAS = ("permit_start_date", "permit_end_date", "Approved Date",
                  "Permit Type", "Agent", "supervisor_district", "permit_number")

    def __init__(self, n_tipos=12, n_agentes=12):
        super().__init__(columnas=list(self.REQUERIDAS))
        self.n_tipos = n_tipos
        self.n_agentes = n_agentes

    def aprender(self, datos):
        return {
            "tipos_principales": list(
                datos["Permit Type"].value_counts().head(self.n_tipos).index),
            "agentes_principales": list(
                datos["Agent"].value_counts().head(self.n_agentes).index),
        }

    def aplicar(self, datos):
        datos["duracion_dias"] = (datos["permit_end_date"]
                                  - datos["permit_start_date"]).dt.days
        datos["n_segmentos"] = datos.groupby("permit_number")["permit_number"].transform("size")
        datos["lag_aprob_inicio"] = (datos["permit_start_date"]
                                     - datos["Approved Date"]).dt.days
        datos["anio_aprobacion"] = datos["Approved Date"].dt.year
        datos["mes_inicio"] = datos["permit_start_date"].dt.month

        datos["tipo_permiso"] = np.where(
            datos["Permit Type"].isin(self._parametros["tipos_principales"]),
            datos["Permit Type"], "Otros")
        datos["agente"] = np.where(
            datos["Agent"].isin(self._parametros["agentes_principales"]),
            datos["Agent"].fillna("Desconocido"), "Otros")
        datos["distrito"] = datos["supervisor_district"].fillna("Desconocido").astype(str)
        return datos


class SaneadorConjunto(Transformador):
    """Descarta columnas sin valor analitico y filas sin variable objetivo.

    Es el unico paso que cambia el numero de filas, y por eso se ejecuta antes
    de la particion: despues, alterar filas invalidaria las mascaras.
    """

    def __init__(self, descartes=None, objetivo="duracion_dias"):
        super().__init__()
        self.descartes = dict(descartes if descartes is not None else DESCARTES)
        self.objetivo = objetivo

    def aprender(self, datos):
        presentes = [c for c in self.descartes if c in datos.columns]
        return {"descartadas": presentes, "filas_entrada": int(len(datos))}

    def aplicar(self, datos):
        datos = datos.drop(columns=self._parametros["descartadas"])
        datos = datos.dropna(subset=[self.objetivo])
        datos = datos.drop_duplicates()
        return datos.reset_index(drop=True)


# =====================================================================
# ETAPA B: despues de la particion (aqui si puede haber fuga)
# =====================================================================


class DerivadorAusencia(Transformador):
    """Codifica la ausencia informativa como variable, en vez de imputarla.

    Materializa el hallazgo de la Fase 2: donde falta el proposito la duracion
    mediana es casi nueve veces mayor, de modo que el hueco es senal y no ruido.
    """

    def __init__(self, n_inspectores=12):
        super().__init__(columnas=["Permit Purpose", "Inspector"])
        self.n_inspectores = n_inspectores

    def aprender(self, datos):
        return {"inspectores_principales":
                list(datos["Inspector"].value_counts().head(self.n_inspectores).index)}

    def aplicar(self, datos):
        datos["tiene_proposito"] = datos["Permit Purpose"].notna().astype(int)
        datos["largo_proposito"] = datos["Permit Purpose"].fillna("").str.len()
        principales = self._parametros["inspectores_principales"]
        datos["inspector"] = np.where(
            datos["Inspector"].isna(), "Sin asignar",
            np.where(datos["Inspector"].isin(principales), datos["Inspector"], "Otros"))
        return datos


class ImputadorMixto(Transformador):
    """Imputa categoricas con etiqueta explicita y numericas con la mediana.

    Heredada de la Fase 2. Alli era una clase suelta con interfaz fit/transform;
    aqui hereda el contrato comun y deja de repetir el control de estado.
    """

    def __init__(self, categoricas, numericas, etiqueta="Desconocido"):
        super().__init__(columnas=list(categoricas) + list(numericas))
        self.categoricas = list(categoricas)
        self.numericas = list(numericas)
        self.etiqueta = etiqueta

    def aprender(self, datos):
        return {"medianas": {c: float(datos[c].median()) for c in self.numericas}}

    def aplicar(self, datos):
        for col in self.categoricas:
            datos[col] = datos[col].fillna(self.etiqueta)
        for col in self.numericas:
            datos[col] = datos[col].fillna(self._parametros["medianas"][col])
        return datos


class CodificadorNominal(Transformador):
    """Convierte una variable nominal en columnas indicadoras 0/1.

    El vocabulario se APRENDE en el ajuste. Una categoria que solo aparece en
    prueba no genera columna, porque el modelo no pudo aprender nada de ella.
    """

    def __init__(self, columna, prefijo=None):
        super().__init__(columnas=[columna])
        self.columna = columna
        self.prefijo = prefijo or columna

    def aprender(self, datos):
        return {"categorias": sorted(datos[self.columna].astype(str).unique())}

    @property
    def columnas_creadas(self):
        return [f"{self.prefijo}_{utilidades.normalizar_nombre(str(c))}"
                for c in self._parametros.get("categorias", [])]

    def aplicar(self, datos):
        valores = datos[self.columna].astype(str)
        for categoria, etiqueta in zip(self._parametros["categorias"],
                                       self.columnas_creadas):
            datos[etiqueta] = (valores == categoria).astype(int)
        return datos


class EscaladorEstandar(Transformador):
    """Centra en cero y escala a desviacion uno, con media y desviacion aprendidas.

    Implementacion propia, equivalente a StandardScaler. Mantener las dos permite
    compararlas en tiempo y memoria (seccion 11) en vez de suponer cual conviene.
    """

    def aprender(self, datos):
        medias, desviaciones = {}, {}
        for col in self.columnas:
            serie = pd.to_numeric(datos[col], errors="coerce")
            medias[col] = float(serie.mean())
            # ddof=0: misma convencion que StandardScaler, que divide por n.
            desv = float(serie.std(ddof=0))
            desviaciones[col] = desv if desv != 0 else 1.0
        return {"medias": medias, "desviaciones": desviaciones}

    def aplicar(self, datos):
        for col in self.columnas:
            datos[col] = ((pd.to_numeric(datos[col], errors="coerce")
                           - self._parametros["medias"][col])
                          / self._parametros["desviaciones"][col])
        return datos


class AgregadorPermiso(Transformador):
    """Lleva el conjunto del segmento de calle al permiso.

    Es la pieza que materializa la decision de unidad de analisis de la Fase 3.
    El objetivo y once de las dieciocho variables son constantes dentro del
    permiso, de modo que repetir la fila no aporta informacion sobre la duracion:
    solo reparte peso. Las cuatro variables que si varian entre segmentos se
    resumen por su valor mas frecuente, y la variacion perdida se conserva en
    indicadores `cruza_*` explicitos.
    """

    def __init__(self, grupo="permit_number", constantes=(), modales=(),
                 medias=(), conservar=()):
        super().__init__(columnas=[grupo])
        self.grupo = grupo
        self.constantes = list(constantes)
        self.modales = list(modales)
        self.medias = list(medias)
        self.conservar = list(conservar)

    def aprender(self, datos):
        no_constantes = [c for c in self.constantes
                         if c in datos.columns
                         and datos.groupby(self.grupo)[c].nunique(dropna=False).gt(1).any()]
        return {"grupos": int(datos[self.grupo].nunique()),
                "filas_entrada": int(len(datos)),
                "constantes_violadas": no_constantes}

    @staticmethod
    def _moda(serie):
        modas = serie.mode(dropna=False)
        return modas.iloc[0] if len(modas) else np.nan

    def aplicar(self, datos):
        if self._parametros["constantes_violadas"]:
            raise ValueError(
                f"{self.nombre}: estas columnas no son constantes dentro del grupo: "
                f"{self._parametros['constantes_violadas']}")
        agrupado = datos.groupby(self.grupo, sort=False)
        partes = {}
        for col in self.constantes + self.conservar:
            if col in datos.columns:
                partes[col] = agrupado[col].first()
        for col in self.modales:
            if col in datos.columns:
                partes[col] = agrupado[col].agg(self._moda)
                partes[f"cruza_{col}"] = agrupado[col].nunique(dropna=False).gt(1).astype(int)
        for col in self.medias:
            if col in datos.columns:
                partes[col] = agrupado[col].mean()
        resultado = pd.DataFrame(partes)
        return resultado.reset_index()


# =====================================================================
# PATRON STRATEGY: varias formas de rellenar un hueco
# =====================================================================


class EstrategiaImputacion:
    """Contrato comun de las estrategias de relleno.

    Strategy separa QUE se hace (rellenar) de COMO se hace (mediana, moda, moda
    por grupo, no rellenar). Permite comparar alternativas sin tocar la clase que
    las usa, que es lo que la Fase 2 hizo por enmascaramiento.
    """

    nombre = "base"

    def aprender(self, datos, columna, agrupador=None):
        raise NotImplementedError

    def rellenar(self, datos, columna, aprendido):
        raise NotImplementedError


class ImputarPorModa(EstrategiaImputacion):
    nombre = "moda global"

    def aprender(self, datos, columna, agrupador=None):
        modas = datos[columna].mode(dropna=True)
        return modas.iloc[0] if len(modas) else np.nan

    def rellenar(self, datos, columna, aprendido):
        return datos[columna].fillna(aprendido)


class ImputarPorModaDeGrupo(EstrategiaImputacion):
    nombre = "moda por grupo"

    def aprender(self, datos, columna, agrupador=None):
        def moda(s):
            m = s.mode(dropna=True)
            return m.iloc[0] if len(m) else np.nan
        return datos.groupby(agrupador)[columna].agg(moda).to_dict()

    def rellenar(self, datos, columna, aprendido, agrupador=None):
        return datos[columna].fillna(datos[agrupador].map(aprendido))


class NoImputar(EstrategiaImputacion):
    nombre = "categoria explicita"

    def aprender(self, datos, columna, agrupador=None):
        return "Desconocido"

    def rellenar(self, datos, columna, aprendido):
        return datos[columna].fillna(aprendido)
