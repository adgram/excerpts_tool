from excerpts import run
import json


if __name__ == "__main__":
    with open("data/数据.json", "r", encoding="utf-8") as f:
        test_data = json.load(f)
    run(file_name="excerpts3.db", tags = test_data["tags"], excerpts = test_data["excerpts"])