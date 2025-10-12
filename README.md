# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                      |    Stmts |     Miss |      Cover |   Missing |
|------------------------------------------ | -------: | -------: | ---------: | --------: |
| src/fire\_prox/\_\_init\_\_.py            |       12 |        0 |    100.00% |           |
| src/fire\_prox/async\_fire\_collection.py |       47 |        0 |    100.00% |           |
| src/fire\_prox/async\_fire\_object.py     |      105 |       23 |     78.10% |89, 111, 117-121, 126-142, 188, 197, 257, 306-310, 315 |
| src/fire\_prox/async\_fire\_query.py      |       81 |        6 |     92.59% |144, 172, 350, 388, 400, 512 |
| src/fire\_prox/async\_fireprox.py         |       25 |        2 |     92.00% |   79, 153 |
| src/fire\_prox/base\_fire\_collection.py  |       16 |        0 |    100.00% |           |
| src/fire\_prox/base\_fire\_object.py      |      198 |       17 |     91.41% |73, 220, 266, 312, 387-388, 392, 396, 421, 424, 447, 522, 614, 668, 685-686, 723 |
| src/fire\_prox/base\_fireprox.py          |       28 |        1 |     96.43% |       154 |
| src/fire\_prox/fire\_collection.py        |       44 |        0 |    100.00% |           |
| src/fire\_prox/fire\_object.py            |      104 |       23 |     77.88% |83, 96-100, 104-107, 119, 134, 140, 202, 272, 300, 330-342 |
| src/fire\_prox/fire\_query.py             |       78 |        6 |     92.31% |142, 170, 347, 384, 396, 505 |
| src/fire\_prox/fire\_vector.py            |       39 |        0 |    100.00% |           |
| src/fire\_prox/fireprox.py                |       21 |        2 |     90.48% |   90, 156 |
| src/fire\_prox/state.py                   |        8 |        0 |    100.00% |           |
| src/fire\_prox/testing/\_\_init\_\_.py    |       86 |       23 |     73.26% |39-43, 53-55, 65-67, 78-87, 90, 103-104, 107 |
|                                 **TOTAL** |  **892** |  **103** | **88.45%** |           |


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