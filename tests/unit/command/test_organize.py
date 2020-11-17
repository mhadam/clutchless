from clutchless.command.organize import ListOrganizeCommandOutput


def test_list_organize_output_shorten_url():
    url = "a"*45
    result = ListOrganizeCommandOutput._shorten_url(url)

    assert result == "a"*37 + "..."
