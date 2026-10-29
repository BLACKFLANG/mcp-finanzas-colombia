"""Pruebas sencillas de los cálculos (no necesitan internet).

Ejecuta:  pytest
"""
import asyncio

import pytest

import servidor
from mcp.server.mcpserver.exceptions import ToolError


def test_cuota_conocida():
    # 1.000.000 al 1% mensual (12,6825% E.A.) a 12 meses -> cuota de 88.849 (valor de tabla)
    resultado = servidor.simular_credito(1_000_000, 12.682503, 12)
    assert resultado["cuota_mensual"] == 88_849
    assert resultado["tasa_mensual_porcentaje"] == 1.0


def test_credito_sin_intereses():
    resultado = servidor.simular_credito(1_200_000, 0, 12)
    assert resultado["cuota_mensual"] == 100_000
    assert resultado["total_intereses"] == 0


def test_plazo_invalido_da_error():
    with pytest.raises(ToolError):
        servidor.simular_credito(1_000_000, 20, 0)


def test_conversion_en_los_dos_sentidos():
    assert servidor.calcular_conversion(100, "USD", 4000)["monto_cop"] == 400_000
    assert servidor.calcular_conversion(400_000, "cop", 4000)["monto_usd"] == 100


def test_el_servidor_publica_4_herramientas():
    herramientas = asyncio.run(servidor.servidor.list_tools())
    nombres = sorted(h.name for h in herramientas)
    assert nombres == ["convertir_moneda", "simular_credito", "trm_hoy", "trm_por_fecha"]
