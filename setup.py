from setuptools import setup

setup(name='domino',
      version='0.3',
      description='Read domino emails.',
      url='https://bitbucket.org/buildupthatwall/domino',
      license='MIT',
      author='Carl Harris',
      author_email='elgoogemail2007@gmail.com',
      packages=['domino'],
      install_requires=['requests', 'beautifulsoup4'],
      zip_safe=False)
