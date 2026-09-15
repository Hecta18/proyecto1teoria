# Lee un archivo de texto con expresiones regulares y cadenas de simbolos,
# cada uno en una línea, la ejecución completa es:
#   1) tokenización + concatenación implícita (infix)
#   2) conversión a postfix (Shunting Yard, shunting_yard_regex.py)
#   3) construcción del árbol sintáctico
#   4) construcción del AFN con el algoritmo de Thompson (lectura depth first de árbol)
#   5) impresion del AFN en consola
#   6) construcción del AFD por construcción directa (followpos), a partir
#      del mismo árbol sintáctico (construccion_directa_afd.py)
#   7) dibujo del AFN y del AFD (afd_dibujo_simulacion.py)
#   8) simulación de cada cadena contra el AFN y contra el AFD
#   9) impresion del resultado de ambas simulaciones y verificación de que
#      coinciden (deben reconocer el mismo lenguaje)

import os
import sys

import regex_tokenize
import shunting_yard_regex as shyR
import Arbol_sintactico as arbol
import thompson_arbol as thompson
import construccion_directa_afd as afd_directo
import afd_dibujo_simulacion as afd_mod

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
                       directorio_afds: str = "AFDs",
                       mostrar_afn: bool = True) -> tuple[thompson.AFN, afd_directo.AFD]:
    """Procesa una expresión regular: postfix → árbol → AFN y AFD → JPEG."""
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

    # --- AFN (Thompson) ---
    nfa = thompson.construir_afn_desde_arbol(raiz)
    print("\nAFN (Thompson):")
    thompson.imprimir_afn(nfa)

    slug = thompson._slug_desde_regex(regex)
    nombre_afn = f"afn_{indice:02d}_{slug}"
    thompson.dibujar_afn(nfa, nombre_afn, directorio=directorio_afns)

    # --- AFD (construcción directa vía followpos) ---
    print("\nAFD (construcción directa):")
    _, afd = afd_directo.procesar_arbol_a_afd(raiz)
    afd_directo.imprimir_resultado_afd(afd)

    nombre_afd = f"afd_{indice:02d}_{slug}"
    afd_mod.dibujar_afd(afd, nombre_afd, directorio=directorio_afds)

    print()
    return nfa, afd


def procesar_archivo(ruta: str | None = None, directorio_afns: str = "AFNs",
                     directorio_afds: str = "AFDs",
                     mostrar_afn: bool = True) -> None:
    """Procesa expresiones regulares y simula todas las cadenas contra AFN y AFD."""
    ruta = _resolver_ruta_entrada(ruta)
    expresiones, cadenas = leer_expresiones_y_cadenas(ruta)

    if not expresiones:
        print(f"El archivo '{ruta}' no contiene expresiones regulares.")
        return

    if not cadenas:
        print(f"Advertencia: el archivo '{ruta}' no contiene cadenas en la sección "
              f"'{MARCADOR_CADENAS}'.")

    os.makedirs(directorio_afns, exist_ok=True)
    os.makedirs(directorio_afds, exist_ok=True)

    afns: list[thompson.AFN] = []
    afds: list[afd_directo.AFD] = []
    expresiones_ok: list[str] = []
    for i, regex in enumerate(expresiones, 1):
        try:
            nfa, afd = procesar_expresion(regex, i, directorio_afns,
                                          directorio_afds=directorio_afds,
                                          mostrar_afn=mostrar_afn)
            afns.append(nfa)
            afds.append(afd)
            expresiones_ok.append(regex)
        except ValueError as exc:
            print(f"Error en expresión {i} ({regex!r}): {exc}")
            print()

    if not afns:
        print("No se construyó ningún AFN/AFD válido.")
        return

    if not cadenas:
        return

    print("=" * 70)
    print("Simulación (todas las cadenas × todos los AFN y AFD):")
    print("-" * 70)

    todo_coincide = True
    for i, (regex, nfa, afd) in enumerate(zip(expresiones_ok, afns, afds), 1):
        for cadena_raw in cadenas:
            cadena = thompson.normalizar_cadena(cadena_raw)
            aceptada_afn = thompson.simular(nfa, cadena)
            aceptada_afd = afd_mod.simular_afd(afd, cadena)
            coincide = aceptada_afn == aceptada_afd
            todo_coincide = todo_coincide and coincide

            resultado_afn = 'yes' if aceptada_afn else 'no'
            resultado_afd = 'yes' if aceptada_afd else 'no'
            cadena_display = cadena if cadena else 'ε'
            marca = '' if coincide else '  <-- AFN y AFD difieren!'
            print(f"Expresión {i} ({regex}) | Cadena: {cadena_display} | "
                  f"AFN: {resultado_afn} | AFD: {resultado_afd}{marca}")

    print("-" * 70)
    if todo_coincide:
        print("OK: el AFN y el AFD coincidieron en todas las cadenas.")
    else:
        print("ATENCIÓN: hubo discrepancias entre AFN y AFD (revisar arriba).")


if __name__ == "__main__":
    ruta_arg = sys.argv[1] if len(sys.argv) > 1 else None
    procesar_archivo(ruta_arg)