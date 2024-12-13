# Client

## Python

The client software has been designed and tested in Python 3.10, 3.11 and 3.12.
The [Pipfile](../../Pipfile) mentions version 3.10 because this is the Python version
that the server uses by default. Since updating this is hard, all written code is
backwards compatible up to version 3.10. It is up to the user to decide which
Python version greater than or equal to 3.10 is used for running the client software.

If Python >= 3.10 is not yet installed on your system, you can download it at the
[Python website](https://www.python.org/downloads/).
The project contains a [Pipfile](../../Pipfile) which contains all dependencies.
To install these, using [*pipenv*](https://pipenv.pypa.io/en/latest/) is recommended.

## Installation of dependencies

The remaining steps for the client software are as follows:

- Clone the repository on the client pc.
- Open a terminal. Navigate to the directory where you cloned it.
- Enter `python -m pipenv install --python=python` to create a virtual environment and install the dependencies from the Pipfile.
  If you do not want to use *pipenv*, but prefer installing the dependencies in your own environment (f.i. Conda, Mamba, etc.),
  you can use `python -m pip install -r docs/install/requirements.txt`.
- (Optional) If you want to develop the software and run the tests with `pytest` or format the code with `yapf`,
  enter `python -m pipenv install --dev` to install the development packages mentioned in the Pipfile.
- Test your installation using the [example notebook](../example/simple_api_usage.ipynb).
