# 📚 Guía de MkDocs

Esta sección explica cómo está configurada la documentación de GestorPro con **MkDocs Material** y cómo puedes extenderla.

---

## ¿Qué es MkDocs?

[MkDocs](https://www.mkdocs.org/) es un generador de sitios de documentación estáticos escrito en Python. Lee archivos Markdown y los convierte en un sitio web navegable. El tema [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) añade un diseño moderno y funcionalidades avanzadas.

---

## Instalación

```bash
pip install mkdocs mkdocs-material
```

---

## Estructura de archivos

```
mi-proyecto/
├── mkdocs.yml          # Configuración principal
└── docs/
    ├── index.md        # Página de inicio
    ├── integrantes.md
    ├── instalacion.md
    ├── arquitectura.md
    ├── guia.md
    ├── guia_mkdocs.md  # Este archivo
    └── modulos/
        ├── app.md
        ├── database.md
        └── logic.md
```

---

## Configuración (mkdocs.yml)

El archivo `mkdocs.yml` es el cerebro del sitio. Los bloques principales son:

```yaml
site_name: GestorPro — Documentación Oficial
theme:
  name: material
  palette:
    - scheme: default   # Modo claro
    - scheme: slate     # Modo oscuro
  features:
    - navigation.tabs   # Pestañas superiores
    - navigation.top    # Botón "Volver arriba"
    - content.code.copy # Botón copiar en bloques de código

nav:
  - Inicio: index.md
  - Módulos:
      - app.py: modulos/app.md
```

---

## Comandos esenciales

| Comando | Descripción |
|---|---|
| `mkdocs serve` | Servidor local con hot-reload en http://127.0.0.1:8000 |
| `mkdocs build` | Genera el sitio estático en la carpeta `site/` |
| `mkdocs gh-deploy` | Despliega en GitHub Pages automáticamente |

---

## Cómo agregar una nueva página

1. Crea el archivo `.md` dentro de `docs/` (ej: `docs/faq.md`)
2. Agrega la ruta en `mkdocs.yml`:
   ```yaml
   nav:
     - FAQ: faq.md
   ```
3. Recarga el servidor — el cambio se aplica automáticamente

---

## Funcionalidades de Markdown extendido

Gracias a las extensiones `pymdownx`, puedes usar:

### Admonitions (cajas de aviso)

```markdown
!!! note "Título opcional"
    Contenido de la nota.

!!! warning
    Esto es una advertencia.

!!! tip
    Un consejo útil.
```

### Pestañas

````markdown
=== "Mac / Linux"
    ```bash
    source .venv/bin/activate
    ```

=== "Windows"
    ```bat
    .venv\Scripts\activate
    ```
````

### Bloques de código con copia

````markdown
```python
def hola():
    print("GestorPro")
```
````

---

## Visualización local

Desde la carpeta `mi-proyecto/`:

```bash
mkdocs serve
```

Abre tu navegador en **http://127.0.0.1:8000** y los cambios se reflejan en tiempo real al guardar cualquier archivo `.md` o `mkdocs.yml`.

---

## Despliegue en GitHub Pages

```bash
mkdocs gh-deploy
```

Este comando construye el sitio y lo sube a la rama `gh-pages` de tu repositorio, publicándolo en:

```
https://edixon19.github.io/OFICIAL_PROYECTO-/
```
