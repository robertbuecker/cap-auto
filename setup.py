"""
Legacy setup.py for backwards compatibility.
All configuration is in pyproject.toml.
"""
from pathlib import Path

from setuptools import Extension, setup

import numpy as np

try:
    from Cython.Build import cythonize
except ImportError:
    cythonize = None


extensions = []
ty6_pyx = Path(__file__).with_name("cap_auto").joinpath("ty6_cython.pyx")
if ty6_pyx.exists() and cythonize is not None:
    extensions.append(
        Extension(
            "cap_auto.ty6_cython",
            [str(ty6_pyx)],
            include_dirs=[np.get_include()],
        )
    )

if cythonize is not None and extensions:
    extensions = cythonize(extensions, language_level="3")

setup(ext_modules=extensions)
