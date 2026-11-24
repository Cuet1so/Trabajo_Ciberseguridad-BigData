"""Serializa las operaciones de la interfaz; no modifica el motor del experimento.

Streamlit puede interrumpir un rerun mientras Numba aún ejecuta código nativo.
El bloqueo compartido evita otro procesamiento o una lectura a mitad del lote,
también entre sesiones del mismo servidor. La capa workqueue de Numba no admite
invocaciones simultáneas desde varios hilos.
"""
from functools import wraps
from threading import RLock
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")
UI_LOCK = RLock()


def remember_view() -> None:
    """Las pestañas no admiten persist_state; guardamos la selección aparte."""
    import streamlit as st
    st.session_state.last_dashboard_view = st.session_state.dashboard_view


def serialized_ui_operation(function: Callable[P, T]) -> Callable[P, T]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        with UI_LOCK:
            return function(*args, **kwargs)
    return wrapped
