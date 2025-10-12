# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                      |    Stmts |     Miss |      Cover |   Missing |
|------------------------------------------ | -------: | -------: | ---------: | --------: |
| src/fire\_prox/\_\_init\_\_.py            |       13 |        0 |    100.00% |           |
| src/fire\_prox/aggregation.py             |       17 |        2 |     88.24% |   96, 133 |
| src/fire\_prox/async\_fire\_collection.py |       63 |        0 |    100.00% |           |
| src/fire\_prox/async\_fire\_object.py     |      113 |       23 |     79.65% |89, 117-121, 126-142, 188, 271, 322-328, 333 |
| src/fire\_prox/async\_fire\_query.py      |      146 |       20 |     86.30% |146, 174, 352, 403, 457, 512, 584-586, 588-590, 601, 604, 608, 611, 662, 674, 838, 846 |
| src/fire\_prox/async\_fireprox.py         |       23 |        2 |     91.30% |   79, 153 |
| src/fire\_prox/base\_fire\_collection.py  |       23 |        1 |     95.65% |       214 |
| src/fire\_prox/base\_fire\_object.py      |      208 |       18 |     91.35% |75, 258, 304, 350, 425-426, 430, 434, 459, 462, 485, 560, 643, 723, 777, 794-795, 832 |
| src/fire\_prox/base\_fireprox.py          |       30 |        1 |     96.67% |       226 |
| src/fire\_prox/fire\_collection.py        |       59 |        0 |    100.00% |           |
| src/fire\_prox/fire\_object.py            |      112 |       23 |     79.46% |85, 98-102, 106-109, 121, 136, 288, 316, 348-362 |
| src/fire\_prox/fire\_query.py             |      143 |       19 |     86.71% |144, 172, 349, 400, 453, 507, 579-581, 583-585, 596, 599, 603, 606, 656, 668, 835 |
| src/fire\_prox/fire\_vector.py            |       39 |        0 |    100.00% |           |
| src/fire\_prox/fireprox.py                |       20 |        2 |     90.00% |   91, 157 |
| src/fire\_prox/state.py                   |        8 |        0 |    100.00% |           |
| src/fire\_prox/testing/\_\_init\_\_.py    |       86 |       23 |     73.26% |39-43, 53-55, 65-67, 78-87, 90, 103-104, 107 |
|                                 **TOTAL** | **1103** |  **134** | **87.85%** |           |


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