from docopt import docopt


def test_parse_find():
    argv = ['find', 'some_arg', '-d', 'some_dir']
    from clutchless.parse import find as find_command

    args = docopt(doc=find_command.__doc__, argv=argv)

    assert args == {
        '-d': ['some_dir'],
        '<torrents>': ['some_arg'],
        'find': True
    }
