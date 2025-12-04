# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "mixseek-core"
copyright = "2025, AlpacaTechSolution"
author = "AlpacaTechSolution"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx_rtd_theme",
    "sphinxcontrib.mermaid",
    "sphinx.ext.todo",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "data", "internal"]

# -- MyST configuration ---------------------------------------------------
# MyST-Parser configuration options

myst_enable_extensions = [
    "tasklist",
    "colon_fence",
]

# Suppress warnings for external references and highlighting failures
suppress_warnings = [
    "myst.xref_missing",
    "misc.highlighting_failure",
]

# -- Todo extension configuration --------------------------------------------
# Show todo and todolist directives in output
todo_include_todos = True

# -- Numfig configuration ----------------------------------------------------
# Enable numbered figures, tables, and code-blocks
numfig = True
numfig_secnum_depth = 0

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
