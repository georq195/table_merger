from sales_merger.discovery import discover


def test_files_and_folders_mixed_order(tmp_path):
    (tmp_path/"d").mkdir(); (tmp_path/"d"/"b.csv").write_text("x"); (tmp_path/"d"/"A.xlsx").write_text("x")
    (tmp_path/"z.csv").write_text("x")
    r = discover([str(tmp_path/"z.csv"), str(tmp_path/"d")])
    assert [p.name for p in r.files] == ["z.csv", "A.xlsx", "b.csv"]

def test_folder_ignores_other_extensions_and_subfolders(tmp_path):
    (tmp_path/"notes.txt").write_text("x"); (tmp_path/"sub").mkdir(); (tmp_path/"sub"/"x.csv").write_text("x")
    (tmp_path/"ok.xls").write_text("x")
    assert [p.name for p in discover([str(tmp_path)]).files] == ["ok.xls"]

def test_lock_files_skipped(tmp_path):
    (tmp_path/"~$report.xlsx").write_text("x"); (tmp_path/"s.xlsx").write_text("x")
    r = discover([str(tmp_path)])
    assert [p.name for p in r.files] == ["s.xlsx"] and r.problems == []

def test_same_file_twice_once(tmp_path):
    f = tmp_path/"a.csv"; f.write_text("x"); (tmp_path/"x").mkdir()
    assert len(discover([str(f), f"{tmp_path}/x/../a.csv"]).files) == 1

def test_problems(tmp_path):
    (tmp_path/"a.txt").write_text("x")
    r = discover([str(tmp_path/"a.txt"), str(tmp_path/"nope.csv")])
    assert r.files == [] and [x[1] for x in r.problems] == ["неподдерживаемый формат файла", "путь не найден"]
