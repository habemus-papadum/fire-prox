# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                      |    Stmts |     Miss |      Cover |   Missing |
|------------------------------------------ | -------: | -------: | ---------: | --------: |
| src/fire\_prox/\_\_init\_\_.py            |       12 |        0 |    100.00% |           |
| src/fire\_prox/async\_fire\_collection.py |       41 |        6 |     85.37% |     90-96 |
| src/fire\_prox/async\_fire\_object.py     |       73 |        9 |     87.67% |89, 104, 109-110, 146, 152, 187, 229, 234 |
| src/fire\_prox/async\_fire\_query.py      |       50 |        3 |     94.00% |140, 168, 363 |
| src/fire\_prox/async\_fireprox.py         |       26 |        2 |     92.31% |   79, 153 |
| src/fire\_prox/base\_fire\_collection.py  |       14 |        0 |    100.00% |           |
| src/fire\_prox/base\_fire\_object.py      |      133 |       13 |     90.23% |72, 184, 290-291, 295, 299, 304, 319, 322, 345, 405, 447, 457 |
| src/fire\_prox/base\_fireprox.py          |       26 |        1 |     96.15% |        93 |
| src/fire\_prox/fire\_collection.py        |       38 |        2 |     94.74% |     94-95 |
| src/fire\_prox/fire\_object.py            |       74 |       15 |     79.73% |83, 88, 95-96, 100, 143, 149, 195, 220, 247-254 |
| src/fire\_prox/fire\_query.py             |       47 |        3 |     93.62% |139, 167, 359 |
| src/fire\_prox/fire\_vector.py            |       39 |        0 |    100.00% |           |
| src/fire\_prox/fireprox.py                |       22 |        2 |     90.91% |   90, 156 |
| src/fire\_prox/state.py                   |        8 |        0 |    100.00% |           |
| src/fire\_prox/testing/\_\_init\_\_.py    |       86 |       23 |     73.26% |39-43, 53-55, 65-67, 78-87, 90, 103-104, 107 |
|                                 **TOTAL** |  **689** |   **79** | **88.53%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/habemus-papadum/fire-prox/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/habemus-papadum/fire-prox/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fhabemus-papadum%2Ffire-prox%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.