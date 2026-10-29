# Guía técnica: cómo funciona por dentro

Todo el servidor está en un solo archivo, `servidor.py`. Esta guía lo explica por partes.

---

## 1. Crear el servidor

```python
from mcp.server.mcpserver import MCPServer

servidor = MCPServer("finanzas-colombia")
```

`MCPServer` viene del SDK oficial de MCP para Python (paquete `mcp`, versión 2). El nombre es el que verá Claude Desktop.

---

## 2. Publicar herramientas

```python
@servidor.tool()
def trm_hoy() -> dict:
    """Devuelve la TRM vigente hoy: el valor oficial de 1 dólar en pesos colombianos."""
    return consultar_trm()
```

- `@servidor.tool()` es un **decorador**: convierte la función en una herramienta que el asistente puede usar.
- El **docstring** es lo que lee el asistente para saber cuándo usarla. Por eso debe ser claro.
- Los **type hints** (`monto: float`, `plazo_meses: int`) le dicen al asistente qué tipo de dato enviar. El SDK los usa para validar.

---

## 3. Consultar la TRM (`consultar_trm`)

La TRM se pide a una API pública de datos.gov.co con la librería `httpx`:

```python
respuesta = httpx.get(URL_TRM, params=parametros, timeout=10)
respuesta.raise_for_status()
filas = respuesta.json()
```

- `params` son los filtros de la consulta. Esta API usa un lenguaje parecido a SQL:
  - Para la TRM más reciente: ordenar por fecha descendente y traer 1 fila (`$order`, `$limit`).
  - Para una fecha: buscar la fila cuya vigencia incluya esa fecha (`$where`).
- `timeout=10` evita que el servidor se quede esperando para siempre.
- `raise_for_status()` lanza un error si la API responde con un fallo.

Cada fila trae `valor` (la TRM), `vigenciadesde` y `vigenciahasta`.

---

## 4. Simular un crédito (`simular_credito`)

En Colombia los bancos anuncian la tasa como **efectiva anual (E.A.)**, pero las cuotas son mensuales. Primero se convierte:

```
tasa_mensual = (1 + tasa_EA) ^ (1/12) - 1
```

Luego la cuota fija (sistema francés, el más común):

```
cuota = monto × tasa_mensual / (1 - (1 + tasa_mensual) ^ -plazo)
```

Ejemplo: 10.000.000 al 24,5 % E.A. a 36 meses → tasa mensual de 1,843 % → cuota de $382.499. En total se pagan $13.769.964, de los cuales $3.769.964 son intereses.

---

## 5. Errores claros (`ToolError`)

```python
if not 1 <= plazo_meses <= 360:
    raise ToolError("El plazo debe estar entre 1 y 360 meses.")
```

Con `ToolError`, el mensaje le llega al asistente tal cual, y este se lo puede explicar al usuario o corregir los datos. Si se lanzara un error común, el asistente solo vería "Error executing tool", sin saber qué pasó.

---

## 6. Cómo se comunica con Claude (stdio)

```python
if __name__ == "__main__":
    servidor.run()
```

Por defecto el servidor usa **stdio**: Claude Desktop lo arranca como un programa y se hablan por la entrada y salida estándar. Por eso **un servidor stdio nunca debe usar `print()`**: lo que imprima se mezclaría con los mensajes del protocolo.

---

## 7. Las pruebas (`tests/test_servidor.py`)

- Comprueban la cuota con un valor conocido de tabla: 1.000.000 al 1 % mensual a 12 meses da $88.849.
- Revisan la conversión de moneda con una TRM fija (`calcular_conversion` está separada justo para poder probarla sin internet).
- Verifican que el servidor publique sus 4 herramientas.

---

## Preguntas para practicar

1. ¿Qué es MCP y qué problema resuelve?
2. ¿Qué diferencia hay entre este servidor MCP y un agente con function calling?
3. ¿Cómo sabe Claude qué herramientas existen y cuándo usarlas?
4. ¿Qué es stdio y por qué no se puede usar `print()` en este servidor?
5. ¿Por qué se convierte la tasa E.A. a tasa mensual?
6. ¿Qué pasa si la API de datos.gov.co no responde?
7. ¿Por qué se usa `ToolError` en vez de un error común?
8. ¿Cómo agregarías una herramienta nueva, por ejemplo para simular un CDT?
