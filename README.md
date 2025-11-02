# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                      |    Stmts |     Miss |      Cover |   Missing |
|------------------------------------------ | -------: | -------: | ---------: | --------: |
| src/fire\_prox/\_\_init\_\_.py            |       12 |        0 |    100.00% |           |
| src/fire\_prox/aggregation.py             |       17 |        2 |     88.24% |   96, 133 |
| src/fire\_prox/async\_fire\_collection.py |      102 |        3 |     97.06% |   286-296 |
| src/fire\_prox/async\_fire\_object.py     |      115 |       15 |     86.96% |68, 95, 97, 154, 222, 288, 295-302, 362, 364 |
| src/fire\_prox/async\_fire\_query.py      |      149 |       22 |     85.23% |151, 179, 357, 412-419, 466, 520, 575, 647-649, 651-653, 664, 667, 671, 674, 725, 737, 901, 909 |
| src/fire\_prox/async\_fireprox.py         |       26 |        2 |     92.31% |   80, 143 |
| src/fire\_prox/base\_fire\_collection.py  |       37 |        2 |     94.59% |   84, 274 |
| src/fire\_prox/base\_fire\_object.py      |      279 |       21 |     92.47% |73-76, 144, 209, 221, 236, 254, 476, 522, 597-598, 602, 606, 632, 635, 658, 733, 816, 943, 993 |
| src/fire\_prox/base\_fireprox.py          |       47 |        3 |     93.62% |228, 292-293 |
| src/fire\_prox/fire\_collection.py        |       95 |        3 |     96.84% |   287-297 |
| src/fire\_prox/fire\_object.py            |       99 |       14 |     85.86% |63, 85, 87, 144, 274, 281-288, 352, 354 |
| src/fire\_prox/fire\_query.py             |      146 |       21 |     85.62% |149, 177, 354, 409-416, 463, 516, 570, 642-644, 646-648, 659, 662, 666, 669, 719, 731, 898 |
| src/fire\_prox/fireprox.py                |       19 |        2 |     89.47% |   92, 147 |
| src/fire\_prox/state.py                   |        8 |        0 |    100.00% |           |
| src/fire\_prox/testing/\_\_init\_\_.py    |       84 |       23 |     72.62% |37-41, 51-53, 63-65, 76-85, 88, 101-102, 105 |
|                                 **TOTAL** | **1235** |  **133** | **89.23%** |           |


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