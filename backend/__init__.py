# Copyright (c) 2024 DatenJäger. All rights reserved.
# backend/__init__.py - capa backend desacoplada de la interfaz

"""Capa backend de DatenJäger.

Agrupa la lógica de negocio que antes vivía mezclada con CustomTkinter:
servicios, estado de aplicación y el punto de entrada de comandos.

Regla de la capa: ningún módulo de ``backend`` importa
``customtkinter``/``tkinter`` ni depende de que exista una ventana abierta.
"""