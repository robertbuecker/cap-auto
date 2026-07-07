"""
Legacy setup.py for backwards compatibility.
All configuration is in pyproject.toml.
"""
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext as _build_ext

import numpy as np


extensions = []
ty6_pyx = Path("cap_auto") / "ty6_cython.pyx"
ty6_c = Path("cap_auto") / "ty6_cython.c"
ty6_cpp = Path("cap_auto") / "ty6_cpp.cpp"
if ty6_pyx.exists():
    extensions.append(
        Extension(
            "cap_auto.ty6_cython",
            [str(ty6_c)],
            include_dirs=[np.get_include()],
        )
    )
if ty6_cpp.exists():
    extensions.append(
        Extension(
            "cap_auto.ty6_cpp",
            [str(ty6_cpp)],
            include_dirs=[np.get_include()],
            language="c++",
        )
    )


class build_ext(_build_ext):
    def run(self):
        if ty6_pyx.exists():
            try:
                from Cython.Build import cythonize
            except ImportError:
                cythonize = None
            if cythonize is not None and not ty6_c.exists():
                cythonize(
                    [
                        Extension(
                            "cap_auto.ty6_cython",
                            [str(ty6_pyx)],
                            include_dirs=[np.get_include()],
                        )
                    ],
                    language_level="3",
                )

        super().run()


setup(ext_modules=extensions, cmdclass={"build_ext": build_ext})
