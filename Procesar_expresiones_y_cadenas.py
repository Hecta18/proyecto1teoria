# Lee un archivo de texto con expresiones regulares y cadenas de simbolos,
# cada uno en una línea, la ejecución completa es:
#   1) tokenización + concatenación implícita (infix)
#   2) conversión a postfix (Shunting Yard, shunting_yard_regex.py)
#   3) construcción del árbol sintáctico
#   4) construcción del AFN con el algoritmo de Thompson (lectura depth first de árbol)
#   5) impresion del AFN en consola
#   6) simulación del AFN con la cadena de simbolos
#   7) impresion del resultado de la simulación en consola

import os
import sys

import regex_tokenize
import shunting_yard_regex as shyR
import Arbol_sintactico as arbol
import thompson_arbol as thompson

MARCADOR_CADENAS = '# --- Cadenas ---'
RUTAS_ENTRADA = ('expresiones_y_cadenas', 'expresiones_y_cadenas.txt')


def _es_comentario(linea: str) -> bool:
    return linea.startswith('#') and linea != MARCADOR_CADENAS


def leer_expresiones_y_cadenas(ruta: str) -> tuple[list[str], list[str]]:
    """Lee el archivo y devuelve (expresiones, cadenas) en dos secciones."""
    with open(ruta, encoding='utf-8') as archivo:
        lineas_raw = archivo.readlines()

    expresiones: list[str] = []
    cadenas: list[str] = []
    seccion_cadenas = False

    for linea_raw in lineas_raw:
        linea = linea_raw.rstrip('\n\r')
        if linea.strip() == MARCADOR_CADENAS:
            seccion_cadenas = True
            continue
        if _es_comentario(linea.strip()):
            continue

        if seccion_cadenas:
            cadenas.append(linea)
        elif linea.strip():
            expresiones.append(linea.strip())

    return expresiones, cadenas


def _resolver_ruta_entrada(ruta: str | None = None) -> str:
    if ruta and os.path.isfile(ruta):
        return ruta
    for candidata in RUTAS_ENTRADA:
        if os.path.isfile(candidata):
            return candidata
    raise FileNotFoundError(
        "No se encontró el archivo de entrada. "
        f"Coloque 'expresiones_y_cadenas' o 'expresiones_y_cadenas.txt' en el directorio actual."
    )


def procesar_expresion(regex: str, indice: int, directorio_afns: str,
                       mostrar_afn: bool = True) -> thompson.AFN:
    """Procesa una expresión regular: postfix → árbol → AFN → JPEG."""
    print("=" * 70)
    print(f"Expresión {indice}: {regex}")
    print("-" * 70)

    tokens = regex_tokenize.tokenize(regex)
    tokens_concat = shyR.insertar_concatenacion_implicita(tokens)
    postfix = shyR.shunting_yard_regex(tokens_concat)

    print(f"Tokens               : {' '.join(tokens)}")
    print(f"Con concatenación (.): {' '.join(tokens_concat)}")
    print(f"Postfix              : {''.join(postfix)}")

    mensajes = shyR.describir_postfix(postfix)
    print("Lectura postfix (derecha -> izquierda):")
    for i, mensaje in enumerate(mensajes, 1):
        print(f"  {i}. {mensaje}")

    raiz = arbol.construir_arbol(postfix)
    print("\nÁrbol sintáctico (texto):")
    arbol.imprimir_arbol(raiz)

    recorrido = arbol.recorrido_postorden(raiz)
    print(f"\nRecorrido postorden (DFS): {' '.join(recorrido)}")

    nfa = thompson.construir_afn_desde_arbol(raiz)
    print("\nAFN (Thompson):")
    thompson.imprimir_afn(nfa)

    slug = thompson._slug_desde_regex(regex)
    nombre = f"afn_{indice:02d}_{slug}"
    thompson.dibujar_afn(nfa, nombre, directorio=directorio_afns)
    print()
    return nfa


def procesar_archivo(ruta: str | None = None, directorio_afns: str = "AFNs",
                     mostrar_afn: bool = True) -> None:
    """Procesa expresiones regulares y simula todas las cadenas contra todos los AFN."""
    ruta = _resolver_ruta_entrada(ruta)
    expresiones, cadenas = leer_expresiones_y_cadenas(ruta)

    if not expresiones:
        print(f"El archivo '{ruta}' no contiene expresiones regulares.")
        return

    if not cadenas:
        print(f"Advertencia: el archivo '{ruta}' no contiene cadenas en la sección "
              f"'{MARCADOR_CADENAS}'.")

    os.makedirs(directorio_afns, exist_ok=True)

    afns: list[thompson.AFN] = []
    for i, regex in enumerate(expresiones, 1):
        try:
            nfa = procesar_expresion(regex, i, directorio_afns, mostrar_afn=mostrar_afn)
            afns.append(nfa)
        except ValueError as exc:
            print(f"Error en expresión {i} ({regex!r}): {exc}")
            print()

    if not afns:
        print("No se construyó ningún AFN válido.")
        return

    if not cadenas:
        return

    print("=" * 70)
    print("Simulación (todas las cadenas × todos los AFN):")
    print("-" * 70)

    for i, (regex, nfa) in enumerate(zip(expresiones[:len(afns)], afns), 1):
        for cadena_raw in cadenas:
            cadena = thompson.normalizar_cadena(cadena_raw)
            aceptada = thompson.simular(nfa, cadena)
            resultado = 'yes' if aceptada else 'no'
            cadena_display = cadena if cadena else 'ε'
            print(f"AFN {i} | Expresión: {regex} | Cadena: {cadena_display} | "
                  f"Resultado: {resultado}")


if __name__ == "__main__":
    ruta_arg = sys.argv[1] if len(sys.argv) > 1 else None
    procesar_archivo(ruta_arg)
