from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()

setup(
    name='followthemoney-ocds',
    version='0.2.0',
    author='Organized Crime and Corruption Reporting Project',
    author_email='data@occrp.org',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=[],
    include_package_data=True,
    package_data={},
    zip_safe=False,
    install_requires=[
        'followthemoney >= 1.29.5',
    ],
    entry_points={
        'babel.extractors': {
            'ftmmodel = followthemoney.messages:extract_yaml'
        },
        'followthemoney.cli': {
            'ocds = ftmocds.cli:import_ocds',
        },
    },
    tests_require=['coverage', 'nose']
)
