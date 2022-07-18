from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

setup(
    name='integrator',
    py_modules=['integrator'],
    entry_points={
        'console_scripts': ['integrator = integrator:start']},
    ext_modules=[
        Pybind11Extension("integrator_cpp", sorted(["./integrator.cpp"]))
    ],
    cmdclass={"build_ext": build_ext},
)
