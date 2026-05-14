import pytest
import os
from datetime import date
from unittest.mock import patch, MagicMock

import streamlit as st
from database import (
    _get_dsn,
    db_add_task,
    db_update_task,
    db_delete_task,
    db_load_tasks
)

# ══════════════════════════════════════════════
# TESTS DE CONFIGURACIÓN
# ══════════════════════════════════════════════

def test_get_dsn_fallback(monkeypatch):
    monkeypatch.setattr(st, "secrets", {})
    monkeypatch.delenv("DATABASE_URL", raising=False)
    dsn = _get_dsn()
    assert "postgresql://postgres" in dsn

def test_get_dsn_env_var(monkeypatch):
    monkeypatch.setattr(st, "secrets", {})
    monkeypatch.setenv("DATABASE_URL", "postgresql://test-env-url")
    assert _get_dsn() == "postgresql://test-env-url"

def test_get_dsn_secrets(monkeypatch):
    mock_secrets = {"supabase": {"url": "postgresql://test-secret-url"}}
    monkeypatch.setattr(st, "secrets", mock_secrets)
    assert _get_dsn() == "postgresql://test-secret-url"

# ══════════════════════════════════════════════
# TESTS DE CRUD DE TAREAS (Mockeando la BD)
# ══════════════════════════════════════════════

@patch('database._exec')
def test_db_add_task(mock_exec):
    # Simulamos que el _exec de INSERT INTO tasks devuelve True
    mock_exec.return_value = True
    
    result = db_add_task(
        title="Nueva tarea de prueba",
        description="Descripción de la tarea",
        priority="High",
        category="Desarrollo",
        status="Pendiente",
        due_date=date(2026, 12, 31),
        assignee="Dev",
        tags=["test", "pytest"]
    )
    
    assert result is True
    assert mock_exec.call_count >= 1
    
    # Verificamos la primera llamada a _exec (la de insertar la tarea)
    args, kwargs = mock_exec.call_args_list[0]
    sql_query = args[0]
    sql_params = args[1]
    
    assert "INSERT INTO tasks" in sql_query
    assert sql_params[1] == "Nueva tarea de prueba"  # title
    assert sql_params[3] == "High"  # priority

@patch('database._exec')
def test_db_update_task(mock_exec):
    mock_exec.return_value = True
    
    # Actualizamos sólo el estado y la prioridad
    result = db_update_task("fake-uuid", status="Completada", priority="Low")
    
    assert result is True
    args, kwargs = mock_exec.call_args_list[0]
    sql_query = args[0]
    sql_params = args[1]
    
    assert "UPDATE tasks SET" in sql_query
    assert "status = %s" in sql_query
    assert "priority = %s" in sql_query
    assert "fake-uuid" in sql_params

@patch('database._exec')
def test_db_delete_task(mock_exec):
    mock_exec.return_value = True
    
    result = db_delete_task("fake-uuid", "Tarea a borrar")
    
    assert result is True
    args, kwargs = mock_exec.call_args_list[0]
    sql_query = args[0]
    sql_params = args[1]
    
    assert "DELETE FROM tasks WHERE id = %s" in sql_query
    assert sql_params[0] == "fake-uuid"

@patch('database._exec')
def test_db_load_tasks(mock_exec):
    # Simulamos datos que devolvería la BD
    mock_exec.return_value = [
        {"id": "1", "title": "Tarea 1", "priority": "High", "tags": '["urgente"]', "due_date": date(2026, 1, 1)},
        {"id": "2", "title": "Tarea 2", "priority": "Low", "tags": None, "due_date": None}
    ]
    
    tasks = db_load_tasks()
    
    assert len(tasks) == 2
    # Verificamos que procesó correctamente el JSON de tags y las fechas a string
    assert tasks[0]["tags"] == ["urgente"]
    assert tasks[0]["due_date"] == "2026-01-01"
    
    assert tasks[1]["tags"] == []
