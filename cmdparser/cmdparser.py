#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
コマンド引数の処理を行います。
"""

# Compatible module
from __future__ import absolute_import
from __future__ import unicode_literals

# Buitin module
import argparse
import inspect
import pprint
import re
import sys
import unittest
import collections

# Global variable
__author__ = "Kazuyuki OHMI"
__version__ = "2.4.0"
__date__ = "2017/08/11"
__license__ = "MIT"

class CmdParser(argparse.ArgumentParser):
    """
    引数の処理を行います。
    docstringはspinx形式を使用します。
    関数名をコマンドにしない場合には、argparseを使用します。
    """

    def __init__(self, functions=[], *args, **kwargs):
        """
        コンストラクタ
        デバッグオプションを有効にするには、debug=Falseを設定します。

        :param list functions:  コマンドに設定する関数
        """

        if not isinstance(functions, list):
            raise TypeError("functions use list.")

        # フレームを取得します。
        stacks = inspect.stack()
        caller_frame = stacks[1]
        framerecord = caller_frame[0]

        # docstringを設定します。
        description = framerecord.f_globals.get("__doc__", "")
        if description is not None:
            description = description.strip()

        # ベースクラスの初期化を行います。
        argparse.ArgumentParser.__init__(self, description=description)

        # バージョンオプションを設定します。
        if "__version__" in framerecord.f_globals:
            version = framerecord.f_globals.get("__version__", "")
            self.add_argument('--version', action='version', version=version)

        # デバッグオプションを設定します。
        if kwargs.get("debug") is not None:
            self.add_argument('--debug', action='store_true', default=kwargs.get("debug"), help='debug')

        # 関数をコマンドにします。
        if functions:
            subparsers = self.add_subparsers()

            for func in functions:

                # Sphinx スタイルの docstrings をパースします。
                values = parse_sphinx(func)

                # コマンドを設定します。
                action = subparsers.add_parser(func.__name__, help=values.get("description"))

                action.set_defaults(func=func)

                for name in values:
                    if name == "name":
                        continue
                    if name == "description":
                        continue

                    if values.get(name).get("default") is None:
                        action.add_argument(name,
                            type=values.get(name).get("type"),
                            help=values.get(name).get("usage"))
                    else:
                        # デフォルト値があれば、任意引数にします。
                        action.add_argument("--" + name,
                            type=values.get(name).get("type"),
                            default=values.get(name).get("default"),
                            help=values.get(name).get("usage"))

    def parse_args(self, *args, **kwargs):
        """
        引数を処理します。
        """

        # 引数を処理します。
        result = super(CmdParser, self).parse_args()

        return result

    def call(self, *args, **kwargs):
        """
        関数を実行します。
        """

        # 引数を処理します。。
        parsed_arg = self.parse_args()

        values = vars(parsed_arg)
        values.update(kwargs)

        # コマンドを処理します。
        if hasattr(parsed_arg, 'func'):
            result = parsed_arg.func(*args, **values)
        else:
            self.error(u'引数が不足しています。')
            sys.exit(-1)

        return result

def parse_sphinx(func, *args, **kwargs):
    """
    Sphinx スタイルの docstrings をパースします(廃止予定->parse_sphinx2)。

    :param function func: 関数
    :rtype:               dict
    :return:              関数の引数
    """

    values = collections.OrderedDict()
    func_doc = func.__doc__

    # ソースコードを取得します。
    _src = inspect.getsource(func)

    # デフォルトパラメータを取得します。
    argspec = inspect.getargspec(func)
    arg_names = list(argspec.args)

    # 後ろから引き当てます。
    arg_names.reverse()
    if argspec.defaults is None:
        arg_values = list()
    else:
        arg_values = list(argspec.defaults)

    args_default = dict()
    for arg_name in arg_names:
        if len(arg_values) != 0:   
            default_value = arg_values.pop(0)
        else:
            default_value = None
        args_default[arg_name] = default_value

    # name
    values["name"] = func.__name__

    # description を設定します。
    if func_doc is not None:
        m_desc = re.search(r"([\s\S]*?):", func_doc)
    else:
        m_desc = None
    
    if m_desc:
        values["description"] = m_desc.group(1).strip()
    else:
        values["description"] = ""


    # パラメータを設定します。
    if func_doc is not None:
        fileds = re.findall(r"(\S*:.*?:.*)", func_doc)
        for filed_line in fileds:
            match = re.search(r":param\s*(.*)\s(.+):(.*)", filed_line)
            if match:
                typ = None
                txt_type = match.group(1).strip()
                txt_name = match.group(2).strip()
                txt_help = match.group(3).strip()

                """
                Python 3 renamed the unicode type to str, the old str type has been replaced by bytes.
                """
                if txt_type == "int":
                    typ = int
                elif txt_type == "str":
                    typ = str
                elif txt_type == "b":
                    typ = str
                elif txt_type == "unicode":
                    typ = unicode
                elif txt_type == "u":
                    typ = unicode
                elif txt_type == "list":
                    typ = list
                elif txt_type == "tuple":
                    typ = tuple
                elif txt_type == "bytes":
                    typ = bytes
                elif txt_type == "bool":
                    typ = bool

                values[txt_name] = {"help": txt_help, "type":typ}

                if args_default.get(txt_name) is not None:
                    values[txt_name]["default"] = args_default.get(txt_name)
                    values[txt_name]["help"] += " (%s)" % str(args_default.get(txt_name))

            match = re.search(r":type\s*(.*):(.*)", filed_line)
            if match:
                typ = None
                txt_name = match.group(1).strip()
                txt_type = match.group(2).strip()

                if txt_type == "int":
                    typ = int
                elif txt_type == "str":
                    typ = str
                elif txt_type == "list":
                    typ = list
                elif txt_type == "tuple":
                    typ = tuple
                elif txt_type == "bytes":
                    typ = bytes
                elif txt_type == "bool":
                    typ = bool

                values[txt_name]["type"] = typ

    return values

def parse_sphinx2(func, *args, **kwargs):
    """
    Sphinx スタイルの docstrings をパースします。

    :param function func: 関数
    :rtype:               OrderedDict
    :return:              関数の引数
    """

    results = collections.OrderedDict()
    func_doc = func.__doc__

    # ソースコードを取得します。
    _src = inspect.getsource(func)

    # デフォルトパラメータを取得します。
    argspec = inspect.getargspec(func)
    arg_names = list(argspec.args)

    # 後ろから引き当てます。
    arg_names.reverse()
    if argspec.defaults is None:
        arg_values = list()
    else:
        arg_values = list(argspec.defaults)

    args_default = dict()
    for arg_name in arg_names:
        if len(arg_values) != 0:   
            default_value = arg_values.pop(0)
        else:
            default_value = None
        args_default[arg_name] = default_value

    # name
    results["name"] = func.__name__

    # description を設定します。
    if func_doc is not None:
        m_desc = re.search(r"([\s\S]*?):", func_doc)
    else:
        m_desc = None
    
    if m_desc:
        results["description"] = m_desc.group(1).strip()
    else:
        results["description"] = ""


    # パラメータを設定します。
    results["args"] = []
    for arg_name in arg_names:
        arg = {}
        arg["name"] = arg_name
        arg["default"] = args_default.get(arg_name)
        pattern = ":param\s*(.*)\s*%s\s*:(.*)" % arg_name
        match = re.search(pattern, func_doc)
        if match is None:
            arg["type"] = None
            arg["help"] = None
        else:            
            arg_type = match.group(1).strip()
            arg_help = match.group(2).strip()

            if arg_type == "int":
                arg["type"] = int
            elif arg_type == "str":
                arg["type"] = str
            elif arg_type == "b":
                arg["type"] = str
            elif arg_type == "unicode":
                arg["type"] = unicode
            elif arg_type == "u":
                arg["type"] = unicode
            elif arg_type == "list":
                arg["type"] = list
            elif arg_type == "tuple":
                arg["type"] = tuple
            elif arg_type == "bytes":
                arg["type"] = bytes
            elif arg_type == "bool":
                arg["type"] = bool

            arg[help] = arg_help

        results["args"].append(arg)

    return results

def get_functions(mod):
    """
    関数の一覧を取得します。
    :param module mod: モジュール ex.) sys.modules[__name__]
    :rtype:            list
    :return:           関数の一覧
    """

    members = inspect.getmembers(mod)
    functions = [obj for _name, obj in members if (inspect.isfunction(obj))]

    return functions

def dummy(text1, text2="abc", *args, **kwargs):
    """
    テスト関数
    :param str text1:   テキスト
    :type text1:        str
    :param text2:       テキスト
    :type text2:        bytes
    :rtype:             None
    """
    print("text1=%s, text2=%s, debug=%s" % (text1, text2, kwargs.get("debug")))

    return 0

class TestCmdParser(unittest.TestCase):
    """
    テストケース
    """

    parser = None

    def setUp(self):
        sys.stdout.write(os.linesep)

        self.parser = CmdParser(sys.modules[__name__], [dummy])

    def tearDown(self):
        self.parser = None

class Test(unittest.TestCase):
    """
    テストケース
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_parse_sphinx(self):
        sys.stdout.write(os.linesep)

        pprint.pprint(parse_sphinx(dummy))
        self.assertTrue(isinstance(parse_sphinx(dummy), dict))

    def test_get_functions(self):
        sys.stdout.write(os.linesep)

        funcs = get_functions(sys.modules[__name__])
        self.assertTrue(get_functions in funcs)

def main():
    """
    console_scripts entry point
    """

    # 引数の処理を行います。
    parser = CmdParser(sys.modules[__name__], [dummy], debug=False)

    # 引数を処理します。
    result = parser.parse()

    return result

def test(*args, **kwargs):
    """
    test entry point
    """
    # 単体テストを実行します。
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCmdParser)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)

    return 0

if __name__ == "__main__":
    """
    self entry point
    """
    sys.exit(test())
