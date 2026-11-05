"""Dependances FastAPI partagees."""

from typing import Annotated

from fastapi import Depends, Request

from ..services.datagouv import DataGouvClient


def get_client(request: Request) -> DataGouvClient:
    """Recupere le client data.gouv.fr stocke dans le state de l'application."""
    return request.app.state.datagouv


ClientDep = Annotated[DataGouvClient, Depends(get_client)]
