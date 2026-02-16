from setuptools import setup, find_packages

# Read requirements.txt
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="images2kmz",
    version="0.3.0",
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'images2kmz=images2kmz.cli:main',
        ],
    },
    author="Hugo Chisholm",
    description="Create KMZ files from geotagged photos with GeoVerra NavPhoto description",
    url="https://github.com/hugochisholm/images2kmz-gv",
    license="MIT",
    python_requires='>=3.10',
)
