from clutchless.command.organize import ListOrganizeCommandOutput, OrganizeCommand


def test_list_organize_output_shorten_url():
    url = "a" * 45
    result = ListOrganizeCommandOutput._shorten_url(url)

    assert result == "a" * 37 + "..."


def test_organize_command_get_folder_name():
    urls = {"http://test.com/announce"}
    announce_url_to_folder_name = {
        'http://test.com/announce': 'folder'
    }
    folder_name = OrganizeCommand._get_folder_name(urls, announce_url_to_folder_name)

    assert folder_name == "folder"


def test_organize_command_get_folder_name_missing():
    urls = {}
    announce_url_to_folder_name = {
        'http://test.com/announce': 'folder'
    }
    folder_name = OrganizeCommand._get_folder_name(urls, announce_url_to_folder_name)

    assert folder_name == "other_torrents"
