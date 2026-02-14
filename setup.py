from setuptools import setup, find_packages

# Read requirements.txt
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="images2kmz",
    version="0.2.0",
    packages=find_packages(),
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
    python_requires='>=3.7',
)
