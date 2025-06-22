from setuptools import setup, find_packages

setup(
    name="mysql_badger_cli",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pandas",
        "jinja2",
        "numpy"
    ],
    entry_points={
        'console_scripts': [
            'mysql-badger=mysql_badger:main',
        ],
    },
    package_data={
        'mysql_badger': ['templates/*'],
    },
    author="Marian  Simpetru",
    author_email="marian.simpetru@esolutions.ro",
    description="A MySQL slow query log analyzer with HTML report generation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/mosulache/mysqlBadger",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
) 