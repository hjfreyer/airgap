from distutils.core import setup

setup(name='airgap',
      install_requires=['future', 'cryptography', 'pycoin', 'click',
                        'pytest', 'typing', 'parameterized', 'hypothesis',
                        'tox'])
