import os
import ast
import types

import pytest


def load_utils():
    """Load helper functions from Avtopark.py without full deps."""
    root = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(root, 'Avtopark.py')
    with open(path, encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)
    lines = source.splitlines()
    funcs = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {'allowed_file', 'predict_expenses', 'photo_url'}:
            code = '\n'.join(lines[node.lineno-1:node.end_lineno])
            funcs[node.name] = code
    ns = {}
    class App:
        config = {'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg'}}
    ns['app'] = App()
    class Expense:
        pass
    ns['Expense'] = Expense
    def url_for(endpoint, filename=None):
        if endpoint == 'static':
            return f"/static/{filename}"
        return f"/{endpoint}"
    ns['url_for'] = url_for
    for code in funcs.values():
        exec(code, ns)
    return ns['allowed_file'], ns['predict_expenses'], ns['photo_url'], Expense


@pytest.fixture(scope='function')
def utils():
    return load_utils()


class FakeQuery:
    def __init__(self, expenses):
        self._expenses = expenses
    def filter_by(self, **kwargs):
        return self
    def all(self):
        return self._expenses


def test_predict_expenses_returns_zero(utils):
    allowed_file, predict_expenses, photo_url, Expense = utils
    Expense.query = FakeQuery([types.SimpleNamespace(amount=100)])
    assert predict_expenses(1) == 0


def test_predict_expenses_multiple(utils):
    allowed_file, predict_expenses, photo_url, Expense = utils
    amounts = [100, 150, 200]
    Expense.query = FakeQuery([types.SimpleNamespace(amount=a) for a in amounts])
    # avg increase = (200 - 100) / (3 - 1) = 50 -> predicted = 200 + 50 = 250
    assert predict_expenses(1) == 250


def test_allowed_file(utils):
    allowed_file, predict_expenses, photo_url, Expense = utils
    assert allowed_file('photo.png')
    assert allowed_file('picture.JPG')
    assert not allowed_file('document.pdf')


def test_photo_url_http(utils):
    _, _, photo_url, _ = utils
    url = 'http://example.com/image.jpg'
    assert photo_url(url) == url


def test_photo_url_local(utils):
    _, _, photo_url, _ = utils
    assert photo_url('car.jpg') == '/static/car.jpg'
