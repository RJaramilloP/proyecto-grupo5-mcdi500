"""Medición de eficiencia - Grupo 5, Fase 3.

Generado por F3/S2_F3_NucleoAlgoritmico_Eficiencia_POO.ipynb, apartado 17.
No editar a mano: los cambios se hacen en el cuaderno.
"""

import math
import time
import timeit
import tracemalloc

import numpy as np
import pandas as pd


def medir(funcion, *args, **kwargs):
    """Ejecuta la funcion y devuelve (resultado, segundos, memoria_pico_MB).

    `tracemalloc` contabiliza las asignaciones del interprete de Python, de modo
    que la cifra es comparable entre ejecuciones en la misma maquina pero no es
    la memoria residente del proceso.
    """
    tracemalloc.start()
    inicio = time.perf_counter()
    resultado = funcion(*args, **kwargs)
    transcurrido = time.perf_counter() - inicio
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return resultado, transcurrido, pico / 1024 / 1024


def cronometrar(funcion, repeticiones=5, rondas=3):
    """Devuelve el tiempo MENOR por ejecucion, no el promedio.

    El promedio incorpora las interrupciones del sistema operativo; el minimo se
    aproxima al costo real del codigo. Es la misma razon por la que
    `timeit.repeat` existe ademas de `timeit.timeit`.
    """
    tiempos = timeit.repeat(funcion, number=repeticiones, repeat=rondas)
    return min(tiempos) / repeticiones


def comparar_implementaciones(implementaciones, comprobar_equivalencia=True,
                              repeticiones=5, rondas=3, tolerancia=1e-9):
    """Compara varias implementaciones de la MISMA operacion.

    Parametros
    ----------
    implementaciones : dict[str, callable]
        Nombre -> funcion sin argumentos.
    comprobar_equivalencia : bool
        Si es True, exige que todas devuelvan lo mismo antes de comparar. Una
        version mas rapida que entrega otro resultado no es una optimizacion.
    tolerancia : float
        Margen relativo admitido al comparar numeros. No es laxitud: dos sumas
        de los mismos valores en distinto ORDEN no dan bit a bit lo mismo en
        coma flotante, y comparar por igualdad exacta rechazaria equivalencias
        que si lo son.

    Lanza
    -----
    ValueError
        Si las implementaciones no coinciden, o si se pasan menos de dos.
    """
    if len(implementaciones) < 2:
        raise ValueError("Se necesitan al menos dos implementaciones para comparar.")

    salidas = {nombre: fn() for nombre, fn in implementaciones.items()}
    if comprobar_equivalencia:
        nombres = list(salidas)
        referencia = salidas[nombres[0]]
        for nombre in nombres[1:]:
            if not _equivalentes(referencia, salidas[nombre], tolerancia):
                raise ValueError(f"'{nombre}' no coincide con '{nombres[0]}'.")

    filas = []
    for nombre, fn in implementaciones.items():
        segundos = cronometrar(fn, repeticiones=repeticiones, rondas=rondas)
        _, _, memoria = medir(fn)
        filas.append({"implementacion": nombre,
                      "segundos": round(segundos, 6),
                      "memoria_mb": round(memoria, 3)})
    tabla = pd.DataFrame(filas).sort_values("segundos").reset_index(drop=True)
    tabla["razon_vs_mejor"] = (tabla.segundos / tabla.segundos.iloc[0]).round(2)
    return tabla


def _equivalentes(a, b, tolerancia=1e-9):
    """Compara dos resultados de tipo arbitrario con la herramienta adecuada."""
    if isinstance(a, (int, float, np.floating, np.integer)) and \
       isinstance(b, (int, float, np.floating, np.integer)):
        return math.isclose(float(a), float(b), rel_tol=tolerancia, abs_tol=tolerancia)
    if isinstance(a, pd.DataFrame) and isinstance(b, pd.DataFrame):
        try:
            pd.testing.assert_frame_equal(a, b, atol=tolerancia, rtol=tolerancia)
            return True
        except AssertionError:
            return False
    if isinstance(a, pd.Series) and isinstance(b, pd.Series):
        try:
            pd.testing.assert_series_equal(a, b, atol=tolerancia, rtol=tolerancia)
            return True
        except AssertionError:
            return False
    return a == b


def perfil_crecimiento(constructor, tamanos, repeticiones=3, rondas=2):
    """Mide como crece el costo con el tamano de la entrada.

    Un tiempo aislado no dice nada sobre la complejidad; la forma de la curva si.

    Parametros
    ----------
    constructor : dict[str, callable]
        Nombre -> funcion(n) que devuelve una funcion sin argumentos a medir.
    tamanos : iterable of int
    """
    filas = []
    for n in tamanos:
        fila = {"n": n}
        for nombre, fabricar in constructor.items():
            fila[nombre] = round(
                cronometrar(fabricar(n), repeticiones=repeticiones, rondas=rondas) * 1000, 4)
        filas.append(fila)
    tabla = pd.DataFrame(filas)
    columnas = [c for c in tabla.columns if c != "n"]
    if len(columnas) == 2:
        tabla["razon"] = (tabla[columnas[0]] / tabla[columnas[1]]).round(2)
    return tabla


def memoria_dataframe(df, profunda=True):
    """Memoria del DataFrame en MB, contando el contenido real de los objetos."""
    return float(df.memory_usage(deep=profunda).sum()) / 1024 / 1024
