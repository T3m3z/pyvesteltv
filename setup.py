import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(name='pyvesteltv',
      version='0.1.5',
      description='A library to interface with some Vestel TV sets',
      url='https://github.com/T3m3z/pyvesteltv',
      long_description=README,
      long_description_content_type="text/markdown",
      author='Teemu Mikkonen',
      author_email='teemu.mikkonen@iki.fi',
      license='MIT',
      install_requires=["websockets>=6.0"],
      packages=['pyvesteltv']
      )

