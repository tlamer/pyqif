import pytest
import pyqif


def test_header():
    """
    Test gen_header().
    """
    ref = """!Account
Nfoo
Tbar
^
!Type:bar
^
"""
    assert pyqif.gen_header("foo", "bar") == ref


@pytest.mark.parametrize(
    "val,indate,outdate,exp",
    [("12/04/2018", "%d/%m/%Y", "%Y-%m-%d", "2018-04-12"),
     ("2018/04/11", "%Y/%m/%d", "%Y-%m-%d", "2018-04-11"),
     ("01.05.2015", "%d.%m.%Y", "%Y-%m-%d", "2015-05-01")])
def test_date(val, exp, indate, outdate):
    """
    Test process_date().
    """
    assert pyqif.process_date(val, indate, outdate) == exp


def test_config():
    """
    Test configuration parser.
    """
    conf_string = """
---
myaccount:
  items:
    D: date
    M: memo
  substitutions:
    payee:
      foo: bar
...
    """

    conf_object = {
        'items': {
            'D': 'date',
            'M': 'memo'
        },
        'substitutions': {
            'payee': {
                'foo': 'bar'
            }
        }
    }

    assert conf_object == pyqif.parse_account_config(conf_string, 'myaccount')
