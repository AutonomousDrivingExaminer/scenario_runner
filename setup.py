import logging

from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    lines = f.read().split('\n')
    requirements = []
    for line in lines:
        if line.startswith('git+'):
            link, package = line.split('#egg=')
            requirements.append(f'{package} @ {link}#{package}')
        else:
            requirements.append(line)


setup(
    name="srunner",
    version="0.9.15",
    long_description=long_description,
    install_requires=requirements,
    package_data={
        'srunner': ['*/*.xsd']
    },
    include_package_data=True,
    packages=find_packages()
)
