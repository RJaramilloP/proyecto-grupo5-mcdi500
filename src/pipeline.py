"""Orquestación y validación del núcleo algorítmico - Grupo 5, Fase 3.

Generado por F3/S2_F3_NucleoAlgoritmico_Eficiencia_POO.ipynb, apartado 17.
No editar a mano: los cambios se hacen en el cuaderno.
"""

import numpy as np
import pandas as pd

from transformadores import Transformador


class Pipeline:
    """Encadena transformadores y controla el orden de ajuste.

    La mascara de ajuste es el elemento central del diseno. `ajustar(datos)`
    aprende de todo lo que recibe; `ajustar(datos, mascara)` aprende solo de las
    filas marcadas y aplica a todas. Esa diferencia de un argumento es la que
    separa un pipeline con fuga de uno sin ella, y aqui es explicita y medible.
    """

    def __init__(self, pasos=None, nombre="pipeline"):
        self._pasos = []
        self._ajustado = False
        self.nombre = nombre
        for paso in (pasos or []):
            self.agregar(paso)

    def agregar(self, transformador):
        if not isinstance(transformador, Transformador):
            raise TypeError(f"{self.nombre}: se esperaba un Transformador y llego "
                            f"{type(transformador).__name__}.")
        self._pasos.append(transformador)
        return self

    def ajustar(self, datos, mascara=None):
        """Ajusta cada paso y propaga el resultado al siguiente.

        Parametros
        ----------
        datos : pd.DataFrame
        mascara : pd.Series of bool | None
            Filas con las que se aprende. None significa aprender de todo, lo
            que solo es legitimo antes de la particion.
        """
        intermedio = datos.copy()
        for paso in self._pasos:
            if mascara is None:
                base = intermedio
            else:
                if len(mascara) != len(intermedio):
                    raise ValueError(
                        f"{self.nombre}: la mascara tiene {len(mascara)} filas y el "
                        f"conjunto {len(intermedio)}. Un paso cambio el numero de filas "
                        f"despues de la particion.")
                base = intermedio.loc[mascara.to_numpy()]
            paso.ajustar(base)                      # polimorfismo: no se pregunta el tipo
            intermedio = paso.transformar(intermedio)
        self._ajustado = True
        return self

    def transformar(self, datos):
        if not self._ajustado:
            raise RuntimeError(f"{self.nombre}: hay que ajustar antes de transformar.")
        resultado = datos.copy()
        for paso in self._pasos:
            resultado = paso.transformar(resultado)
        return resultado

    def ajustar_transformar(self, datos, mascara=None):
        return self.ajustar(datos, mascara).transformar(datos)

    # ---- alias scikit-learn --------------------------------------------
    def fit(self, X, y=None):
        return self.ajustar(X)

    def transform(self, X):
        return self.transformar(X)

    def fit_transform(self, X, y=None):
        return self.ajustar_transformar(X)

    # ---- introspeccion --------------------------------------------------
    def pasos_ejecutados(self):
        return tuple(self._pasos)

    def resumen(self):
        return pd.DataFrame([
            {"orden": i, "paso": p.nombre, "clase": type(p).__name__,
             "ajustado": p.ajustado, "n_parametros": len(p.parametros)}
            for i, p in enumerate(self._pasos, start=1)])

    def __len__(self):
        return len(self._pasos)

    def __repr__(self):
        estado = "ajustado" if self._ajustado else "sin ajustar"
        return f"Pipeline('{self.nombre}', {len(self._pasos)} pasos, {estado})"


class Validador:
    """Ejecuta las comprobaciones de integridad sobre el conjunto resultante.

    Vive aparte del Pipeline porque responde otra pregunta: el Pipeline dice
    como se construye el conjunto, el Validador dice si sirve. Se ejecuta desde
    el cuaderno y desde la terminal sin arrastrar el pipeline consigo.
    """

    def __init__(self, objetivo=None, grupo=None, prohibidas=(), grupos_one_hot=None,
                 filas_esperadas=None):
        self.objetivo = objetivo
        self.grupo = grupo
        self.prohibidas = list(prohibidas)
        self.grupos_one_hot = dict(grupos_one_hot or {})
        self.filas_esperadas = filas_esperadas
        self._resultados = []

    def _anotar(self, texto, condicion, detalle=""):
        self._resultados.append({"comprobacion": texto,
                                 "resultado": "OK" if condicion else "FALLA",
                                 "detalle": detalle})
        return bool(condicion)

    def validar(self, datos, caracteristicas=None):
        self._resultados = []
        caracteristicas = list(caracteristicas or [])

        nulos = int(datos.isna().sum().sum())
        self._anotar("Sin valores nulos", nulos == 0, f"total = {nulos}")

        if caracteristicas:
            no_num = [c for c in caracteristicas
                      if not pd.api.types.is_numeric_dtype(datos[c])]
            self._anotar("Todas las caracteristicas son numericas", not no_num,
                         f"no numericas: {no_num}")
            import numpy as np
            infinitos = int(np.isinf(datos[caracteristicas]
                                     .to_numpy(dtype="float64")).sum())
            self._anotar("Sin valores infinitos", infinitos == 0,
                         f"infinitos = {infinitos}")

        for nombre, columnas in self.grupos_one_hot.items():
            presentes = [c for c in columnas if c in datos.columns]
            suma = datos[presentes].sum(axis=1) if presentes else None
            # Una fila suma 1 si su categoria estaba en el vocabulario aprendido,
            # y 0 si la categoria solo aparece fuera del entrenamiento. Exigir
            # siempre 1 seria exigir que el codificador hubiera visto la prueba.
            coherente = bool(presentes) and bool(suma.isin([0, 1]).all())
            sin_categoria = int((suma == 0).sum()) if presentes else 0
            self._anotar(f"Grupo one-hot '{nombre}' coherente", coherente,
                         f"{len(presentes)} columnas; {sin_categoria} filas con "
                         f"categoria no vista en ajuste")

        presentes_prohibidas = [c for c in self.prohibidas if c in datos.columns]
        self._anotar("Ninguna variable prohibida presente", not presentes_prohibidas,
                     f"excluidas: {self.prohibidas}")

        if self.objetivo and caracteristicas:
            self._anotar("El objetivo no esta entre las caracteristicas",
                         self.objetivo not in caracteristicas, self.objetivo)

        if self.grupo and "particion" in datos.columns:
            tr = set(datos.loc[datos.particion == "train", self.grupo])
            te = set(datos.loc[datos.particion == "test", self.grupo])
            self._anotar("Sin grupos compartidos entre particiones", not (tr & te),
                         f"{len(tr)} train / {len(te)} test")

        if self.filas_esperadas is not None:
            self._anotar("Filas coinciden con lo declarado",
                         len(datos) == self.filas_esperadas,
                         f"{len(datos)} de {self.filas_esperadas}")
        return self.tabla()

    def tabla(self):
        return pd.DataFrame(self._resultados)

    @property
    def aprobado(self):
        return bool(self._resultados) and all(r["resultado"] == "OK"
                                              for r in self._resultados)
