from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='ConnorLabAnalysisTools',
    version='0.1.16',
    description='Tools for analyzing data in the Connor Lab',
    # long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Allen Chen',
    author_email='allenmuhanchen@gmail.com',
    url='https://github.com/EdConnorLab/ConnorLabAnalysisTools',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=required,
)

