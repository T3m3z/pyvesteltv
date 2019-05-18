from setuptools import setup

setup(name='pyvesteltv',
      version='0.1.1',
      description='A library to interface with some Vestel TV sets',
      url='https://github.com/T3m3z/pyvesteltv',
      author='Teemu Mikkonen',
      author_email='teemu.mikkonen@iki.fi',
      license='MIT',
      install_requires=["websockets==3.3"],
      packages=['pyvesteltv']
      )

