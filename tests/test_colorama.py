from colorama import Fore, init, deinit


def test_colorama(capsys):
    init(autoreset=True)
    print(Fore.GREEN + "hello world")
    deinit()

    result = capsys.readouterr()
    assert result.out == "hello world\n"
