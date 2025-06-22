# MySQL Badger CLI

A command-line tool for MySQL slow query log analysis with HTML report generation.

## Installation

```bash
pip install -e .
```

## Usage

```bash
mysql-badger /path/to/mysql-slow.log
```

The HTML report will be generated in the current directory.

## Development

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```

2. Install development dependencies:
```bash
pip install -e ".[dev]"
```

3. Run tests:
```bash
pytest
``` 