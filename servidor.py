"""Servidor MCP de finanzas para Colombia.

MCP (Model Context Protocol) es un estándar para darle herramientas a un
asistente de IA. Este servidor le da a Claude Desktop (o a cualquier asistente
compatible) 4 herramientas:

    trm_hoy           -> el dólar oficial de hoy en pesos colombianos
    trm_por_fecha     -> el dólar oficial de una fecha pasada
    convertir_moneda  -> pasa de dólares a pesos o de pesos a dólares
    simular_credito   -> calcula la cuota mensual de un préstamo

La TRM se consulta en tiempo real en la API pública de datos.gov.co
(dato oficial de la Superintendencia Financiera).

Ejecuta:  python servidor.py   (normalmente lo arranca Claude Desktop, no tú)
"""
from datetime import date

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError  # error con mensaje claro para el asistente

URL_TRM = "https://www.datos.gov.co/resource/32sa-8pi3.json"

servidor = MCPServer("finanzas-colombia")


# ---------------------------------------------------------------------------
# Funciones de apoyo (no son herramientas, las usan las herramientas)
# ---------------------------------------------------------------------------

def consultar_trm(fecha: str = "") -> dict:
    """Pide la TRM a datos.gov.co. Sin fecha trae la más reciente."""
    if fecha:
        try:
            date.fromisoformat(fecha)  # comprueba que la fecha sea válida
        except ValueError:
            raise ToolError("La fecha debe tener formato AAAA-MM-DD, por ejemplo 2026-01-15.")
        momento = fecha + "T00:00:00"
        parametros = {
            "$where": f"vigenciadesde <= '{momento}' AND vigenciahasta >= '{momento}'",
            "$limit": 1,
        }
    else:
        parametros = {"$order": "vigenciadesde DESC", "$limit": 1}

    respuesta = httpx.get(URL_TRM, params=parametros, timeout=10)
    respuesta.raise_for_status()  # si la API falla, lanza un error
    filas = respuesta.json()
    if not filas:
        raise ToolError(f"No hay TRM publicada para la fecha {fecha}.")

    fila = filas[0]
    return {
        "trm": float(fila["valor"]),
        "vigente_desde": fila["vigenciadesde"][:10],
        "vigente_hasta": fila["vigenciahasta"][:10],
        "fuente": "Superintendencia Financiera de Colombia (datos.gov.co)",
    }


def calcular_conversion(monto: float, de: str, trm: float) -> dict:
    """Convierte con una TRM dada. Separada para poder probarla sin internet."""
    de = de.upper()
    if monto <= 0:
        raise ToolError("El monto debe ser mayor que cero.")
    if de == "USD":
        return {"monto_usd": monto, "monto_cop": round(monto * trm), "trm_usada": trm}
    if de == "COP":
        return {"monto_cop": monto, "monto_usd": round(monto / trm, 2), "trm_usada": trm}
    raise ToolError("La moneda de origen debe ser USD o COP.")


# ---------------------------------------------------------------------------
# Herramientas: el decorador @servidor.tool() las publica para el asistente.
# El docstring de cada una es lo que el asistente lee para saber cuándo usarla.
# ---------------------------------------------------------------------------

@servidor.tool()
def trm_hoy() -> dict:
    """Devuelve la TRM vigente hoy: el valor oficial de 1 dólar en pesos colombianos."""
    return consultar_trm()


@servidor.tool()
def trm_por_fecha(fecha: str) -> dict:
    """Devuelve la TRM (valor oficial del dólar en pesos) de una fecha.
    La fecha va en formato AAAA-MM-DD, por ejemplo 2026-01-15."""
    return consultar_trm(fecha)


@servidor.tool()
def convertir_moneda(monto: float, de: str = "USD") -> dict:
    """Convierte dinero entre dólares y pesos colombianos usando la TRM de hoy.
    'de' es la moneda de origen: USD (dólares) o COP (pesos)."""
    trm = consultar_trm()["trm"]
    return calcular_conversion(monto, de, trm)


@servidor.tool()
def simular_credito(monto: float, tasa_efectiva_anual: float, plazo_meses: int) -> dict:
    """Calcula la cuota mensual fija de un crédito (sistema francés, el más común en Colombia).
    monto: valor del préstamo en pesos. tasa_efectiva_anual: tasa E.A. en porcentaje,
    por ejemplo 24.5. plazo_meses: número de cuotas, de 1 a 360."""
    if monto <= 0:
        raise ToolError("El monto debe ser mayor que cero.")
    if not 0 <= tasa_efectiva_anual < 100:
        raise ToolError("La tasa efectiva anual debe estar entre 0 y 100.")
    if not 1 <= plazo_meses <= 360:
        raise ToolError("El plazo debe estar entre 1 y 360 meses.")

    # Los bancos en Colombia anuncian tasas efectivas anuales (E.A.),
    # pero la cuota se calcula con la tasa mensual equivalente.
    tasa_mensual = (1 + tasa_efectiva_anual / 100) ** (1 / 12) - 1

    if tasa_mensual == 0:
        cuota = monto / plazo_meses
    else:
        cuota = monto * tasa_mensual / (1 - (1 + tasa_mensual) ** -plazo_meses)

    total_pagado = cuota * plazo_meses
    return {
        "cuota_mensual": round(cuota),
        "total_pagado": round(total_pagado),
        "total_intereses": round(total_pagado - monto),
        "tasa_mensual_porcentaje": round(tasa_mensual * 100, 3),
    }


if __name__ == "__main__":
    servidor.run()  # se comunica por stdio (entrada y salida estándar)
