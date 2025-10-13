# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                      |    Stmts |     Miss |      Cover |   Missing |
|------------------------------------------ | -------: | -------: | ---------: | --------: |
| src/fire\_prox/\_\_init\_\_.py            |       13 |        0 |    100.00% |           |
| src/fire\_prox/aggregation.py             |       17 |        2 |     88.24% |   96, 133 |
| src/fire\_prox/async\_fire\_collection.py |       67 |        0 |    100.00% |           |
| src/fire\_prox/async\_fire\_object.py     |       92 |       13 |     85.87% |68, 95, 97, 154, 222, 288, 295-302 |
| src/fire\_prox/async\_fire\_query.py      |      146 |       20 |     86.30% |151, 179, 357, 408, 462, 517, 589-591, 593-595, 606, 609, 613, 616, 667, 679, 843, 851 |
| src/fire\_prox/async\_fireprox.py         |       23 |        2 |     91.30% |   80, 143 |
| src/fire\_prox/base\_fire\_collection.py  |       34 |        1 |     97.06% |       257 |
| src/fire\_prox/base\_fire\_object.py      |      289 |       26 |     91.00% |74-77, 145, 210-212, 215, 227, 242, 260, 482, 528, 603-604, 608, 612, 638, 641, 664, 739, 822, 902, 956, 973-974, 1011 |
| src/fire\_prox/base\_fireprox.py          |       47 |        3 |     93.62% |228, 292-293 |
| src/fire\_prox/fire\_collection.py        |       60 |        0 |    100.00% |           |
| src/fire\_prox/fire\_object.py            |       79 |       12 |     84.81% |63, 85, 87, 144, 274, 281-288 |
| src/fire\_prox/fire\_query.py             |      143 |       19 |     86.71% |149, 177, 354, 405, 458, 512, 584-586, 588-590, 601, 604, 608, 611, 661, 673, 840 |
| src/fire\_prox/fire\_vector.py            |       39 |        0 |    100.00% |           |
| src/fire\_prox/fireprox.py                |       15 |        2 |     86.67% |   90, 145 |
| src/fire\_prox/state.py                   |        8 |        0 |    100.00% |           |
| src/fire\_prox/testing/\_\_init\_\_.py    |       84 |       23 |     72.62% |37-41, 51-53, 63-65, 76-85, 88, 101-102, 105 |
|                                 **TOTAL** | **1156** |  **123** | **89.36%** |           |


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